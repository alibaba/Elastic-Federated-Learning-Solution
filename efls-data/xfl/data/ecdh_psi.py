# Copyright 2021 Alibaba Group Holding Limited. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import uuid
import os

from pyflink.common.typeinfo import Types
from pyflink.datastream.functions import RuntimeContext
from pyflink.datastream.state import ValueStateDescriptor

from xfl.common.common import RunMode
from xfl.data import utils
from xfl.data.store import DictSampleKvStore, LevelDbKvStore
from xfl.data.functions import ClientJoinFunc,ServerSortJoinFunc, record_cmp, get_local_bucket_id
from xfl.data.psi.ecc_signer import EccSigner
from xfl.common.logger import log
from xfl.service import create_data_join_client, create_data_join_server
from xfl.data.utils import get_sample_store_key, split_sample_store_key


class ClientEcdhJoinFunc(ClientJoinFunc):
  def __init__(self,
      job_name: str,
      peer_host: str,
      peer_ip: str,
      peer_port: int,
      bucket_num: int = 64,
      cmp_func=record_cmp,
      sample_store_cls=None,
      batch_size: int = 2048,
      wait_s: int = 1800,
      tls_crt: str = '',
      client2multiserver: int = 1,
      inputfile_type: str = 'tfrecord',
      run_mode: RunMode = RunMode.LOCAL,
      db_root_path='/tmp'):
    self._job_name = job_name
    self._bucket_num = bucket_num
    self._state = None
    self._delay = 10000
    self._peer_host = peer_host
    self._peer_ip = peer_ip
    self._peer_port = peer_port
    self._batch_size = batch_size
    self._run_mode = run_mode
    self._wait_s = wait_s
    self._tls_crt = tls_crt
    self._inputfile_type = inputfile_type
    self._subtask_index = None
    self._initial_bucket = None
    self._client2multiserver = client2multiserver
    self._request_buf = [{} for i in range(self._client2multiserver)]

  def open(self, runtime_context: RuntimeContext):
    log.info("EcdhPsi Client Init...")
    self._signer = EccSigner()
    self._state = runtime_context.get_state(ValueStateDescriptor(
      "last_modified_time", Types.LONG()))

    self._subtask_index = runtime_context.get_index_of_this_subtask()
    #In c2ms mode, each client is corresponding to  #client2multiserver servers.
    #The matching rule: No. 0 client corresponds to No. 0,1,2...#{client2multiserver-1} server.
    self._initial_bucket = self._subtask_index * self._client2multiserver
    if self._run_mode == RunMode.K8S:
      if self._tls_crt is None or len(self._tls_crt) == 0:
        raise RuntimeError("tls crt should not be empty in k8s mode client job!")
    self.cnt = [0 for i in range(self._client2multiserver)]
    self._client = create_data_join_client(host=self._peer_host,
                                     ip=self._peer_ip,
                                     port=self._peer_port,
                                     job_name=self._job_name,
                                     bucket_id=self._subtask_index,
                                     run_mode=self._run_mode,
                                     tls_crt=self._tls_crt,
                                     client2multiserver=self._client2multiserver)
    for i in range(self._client2multiserver):
      cur_bucket_id = self._initial_bucket + i
      log.info("Step1: begin to sign server data for bucket %d."%cur_bucket_id)
      log.info("Client begin to wait... monitered ip %s, port %s, bucket %d"%(self._peer_ip, self._peer_port, cur_bucket_id))
      self._client.wait_ready(timeout=self._wait_s)
      log.info("Server ready bucket %d"%cur_bucket_id)
      batch_cnt = 0
      item_cnt = 0
      while True:
        finished, real_batch_size, block_id, data = self._client.acquire_server_data(bucket_id=cur_bucket_id)
        if finished:
          break
        batch_cnt += 1
        item_cnt += real_batch_size
        if batch_cnt % 100 == 0:
          log.info("Sign server data %d batches."%batch_cnt)
        signed_data = [self._signer.sign(i) for i in data]
        send_ok = self._client.send_server_signed_data(signed_data, block_id, bucket_id=cur_bucket_id)
        #assert send_ok is True
      log.info("Step1: Sign server data ok for bucket %d! total server data item num: %d"%(cur_bucket_id, item_cnt))
    log.info("Step2: Begin to join data..")
    self.cnt_time = 0

  def process_element(self, value, ctx: 'ProcessFunction.Context'):
    if self.cnt_time % 1000 == 0:
      s = self._state.value()
      cur = ctx.timestamp() // 1000 * 1000
      if s is None or cur > s:
        self._state.update(cur)
        ctx.timer_service().register_event_time_timer(cur + self._delay)
    self.cnt_time += 1
    assert(ctx.get_current_key() == self._subtask_index)
    bucket_id = get_local_bucket_id(value[0], self._client2multiserver)
    self.cnt[bucket_id] += 1
    id_key = get_sample_store_key(value[0], value[1])
    self._request_buf[bucket_id][id_key] = value[2]
    if len(self._request_buf[bucket_id]) >= self._batch_size:
      #for ecdh request_ids from client should be singed first
      now_bucket_id = self._initial_bucket + bucket_id
      request_ids = list(self._request_buf[bucket_id].keys())
      signed_request_ids = [self._signer.sign_hash(x) for x in request_ids]
      existence = self._client.sync_join(signed_request_ids, now_bucket_id)
      res_ids = utils.gather_res(request_ids, existence=existence)
      for i in res_ids:
        if self._inputfile_type == 'tfrecord':
          yield str(now_bucket_id), self._request_buf[bucket_id].get(i)
        else :
          yield str(now_bucket_id), self._request_buf[bucket_id].get(i).decode() + '\n'
      log.info("client sync join bucket {} current idx: {}".format(now_bucket_id, self.cnt[bucket_id]))
      self._request_buf[bucket_id].clear()

  def on_timer(self, timestamp: int, ctx: 'KeyedProcessFunction.OnTimerContext'):
    s = self._state.value()
    if timestamp >= s + self._delay:
      #flush buffer
      for bucket_id in range(self._client2multiserver):
        if self._request_buf[bucket_id]:
          #for ecdh request_ids from client should be singed first
          now_bucket_id = self._initial_bucket + bucket_id
          request_ids = list(self._request_buf[bucket_id].keys())
          signed_request_ids = [self._signer.sign_hash(x) for x in request_ids]
          existence = self._client.sync_join(signed_request_ids, now_bucket_id)
          res_ids = utils.gather_res(request_ids, existence=existence)
          for i in res_ids:
            if self._inputfile_type == 'tfrecord':
              yield str(now_bucket_id), self._request_buf[bucket_id].get(i)
            else :
              yield str(now_bucket_id), self._request_buf[bucket_id].get(i).decode() + '\n'
        self._request_buf[bucket_id].clear()
      res = self._client.finish_join()
      if not res:
        raise ValueError("Join finish with error")

class ServerEcdhJoinFunc(ServerSortJoinFunc):
  def __init__(
          self,
          job_name: str,
          port: int = 50051,
          bucket_num: int = 64,
          cmp_func=record_cmp,
          sample_store_cls=DictSampleKvStore,
          batch_size: int = 2048,
          wait_s: int = 1800,
          inputfile_type: str = 'tfrecord',
          run_mode: RunMode = RunMode.LOCAL,
          db_root_path: str = '/tmp',
          **kwargs):
    super().__init__(job_name=job_name,
        port=port,
        bucket_num=bucket_num,
        cmp_func=cmp_func,
        sample_store_cls=sample_store_cls,
        batch_size=batch_size,
        wait_s=wait_s,
        inputfile_type=inputfile_type,
        run_mode=run_mode,
        db_root_path=db_root_path)
    self._ecc_signer = EccSigner()

  def open(self, runtime_context: RuntimeContext):
    super().open(runtime_context)
    self._ecc_signer = EccSigner()
    if self._sample_store_cls is DictSampleKvStore:
      self._ecdh_id_map = DictSampleKvStore()
    elif self._sample_store_cls is LevelDbKvStore:
      db_path='{}-{}-bucket_{}_ecdh'.format(self._job_name, str(uuid.uuid4())[0:6], self._bucket_num)
      self._ecdh_id_map = LevelDbKvStore(path=os.path.join(self._db_root_path, db_path))
    else:
      raise RuntimeError("sample_store_cls is not supported by now{}".format(self._sample_store_cls))


  def process_element(self, value, ctx: 'ProcessFunction.Context'):
    if self.cnt % 1000 == 0:
      s = self._state.value()
      cur = ctx.timestamp() // 1000 * 1000
      if s is None or cur > s:
        self._state.update(cur)
        ctx.timer_service().register_event_time_timer(cur + self._delay)
    key = self._ecc_signer.sign_hash(get_sample_store_key(value[0], value[1]))
    self._sample_store.put(key, value[2])
    self.cnt += 1

  def on_timer(self, timestamp: int, ctx: 'KeyedProcessFunction.OnTimerContext'):
    s = self._state.value()
    if timestamp >= s + self._delay:
      # create join server and wait
      data_join_server, _, k8s_resouce_handler = create_data_join_server(
        port=self._port,
        job_name=self._job_name,
        bucket_id=ctx.get_current_key(),
        sample_kv_store=self._sample_store,
        run_mode=self._run_mode,
        use_psi=True,
        psi_server_type='ecdh',
        signer=self._ecc_signer,
        ecdh_id_map=self._ecdh_id_map
      )
      data_join_server.set_is_ready(True)
      # server wait for 1h
      log.info("ECDH PSI DataJoinServer for bucket {} has been ready, "
               "unique key size: {}, all key size:{}"
               .format(ctx.get_current_key(), self._sample_store.size(), self.cnt))
      data_join_server.wait_for_finish(timeout=self._wait_s)
      log.info("ECDH PSI DataJoinServer for bucket {} finished! "
               "Begin to write sample".format(ctx.get_current_key()))
      for l in data_join_server.get_final_result():
        for i in l:
          local_key = self._ecdh_id_map.get(i)
          if self._inputfile_type == 'tfrecord':
            yield str(ctx.get_current_key()), self._sample_store.get(local_key)
          else :
            yield str(self._subtask_index), self._sample_store.get(i).decode() + '\n'
      self._sample_store.clear()
      self._ecdh_id_map.clear()
      if self._run_mode == RunMode.K8S:
        k8s_resouce_handler.delete()
