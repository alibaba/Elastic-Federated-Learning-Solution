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

from pyflink.datastream.functions import RuntimeContext
from xfl.common.common import RunMode
from xfl.common.logger import log
from xfl.data import utils
from xfl.data.store import DictSampleKvStore
from xfl.data.functions import ClientSortJoinFunc,ServerSortJoinFunc, record_cmp, get_local_bucket_id
from xfl.service import create_data_join_client, create_data_join_server
from xfl.data.utils import get_sample_store_key
from xfl.data.psi.rsa_signer import ServerRsaSigner, ClientRsaSigner

class ClientRsaJoinFunc(ClientSortJoinFunc):
  def __init__(self,
      job_name: str,
      peer_host: str,
      peer_ip: str,
      peer_port: int,
      bucket_num: int = 64,
      cmp_func=record_cmp,
      sample_store_cls=DictSampleKvStore,
      batch_size: int = 2048,
      wait_s: int = 1800,
      tls_crt: str = '',
      client2multiserver: int = 1,
      inputfile_type: str = 'tfrecord',
      run_mode: RunMode = RunMode.LOCAL,
      db_root_path='/tmp',
      timer_delay_s: int = 30):
    super().__init__(
        job_name,
        peer_host,
        peer_ip,
        peer_port,
        bucket_num,
        cmp_func,
        sample_store_cls,
        batch_size,
        wait_s,
        tls_crt,
        client2multiserver,
        inputfile_type,
        run_mode,
        db_root_path,
        timer_delay_s)

  def open(self, runtime_context: RuntimeContext):
    super().open(runtime_context)
    self._client = create_data_join_client(host=self._peer_host,
                                     ip=self._peer_ip,
                                     port=self._peer_port,
                                     job_name=self._job_name,
                                     bucket_id=self._subtask_index,
                                     run_mode=self._run_mode,
                                     tls_crt=self._tls_crt,
                                     client2multiserver=self._client2multiserver)
    self._request_buf = [{} for i in range(self._client2multiserver)]
    self.cnt = [0 for i in range(self._client2multiserver)]
    self._rsa_signer = []
    log.info("RSA Client Begin to fetch public key！")
    for bucket_id in range (self._client2multiserver):
      now_bucket_id = self._initial_bucket + bucket_id
      pub_key_bytes = self._client.request_public_key_from_server(now_bucket_id)
      self._rsa_signer.append(ClientRsaSigner(pub_key_bytes))

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

    #1.blind. 2.send server to sign. 3.deblind and put in sample store.
    self.cnt[bucket_id] += 1
    id_key = get_sample_store_key(value[0], value[1])
    self._request_buf[bucket_id][id_key] = value[2]

    if len(self._request_buf[bucket_id]) >= self._batch_size:
      now_bucket_id = self._initial_bucket + bucket_id
      request_ids = list(self._request_buf[bucket_id].keys())
      signed_request_ids = self._rsa_signer[bucket_id].sign_func(request_ids, self._client, now_bucket_id)
      log.info("client rsa-sign from bucket {} current idx: {}".format(now_bucket_id, self.cnt[bucket_id]))
      for k, sk in zip(request_ids, signed_request_ids):
        self._sample_store[bucket_id].put(sk, self._request_buf[bucket_id][k])
      self._request_buf[bucket_id].clear()

  def on_timer(self, timestamp: int, ctx: 'KeyedProcessFunction.OnTimerContext'):
    s = self._state.value()
    if timestamp >= s + self._delay:
      self._client.wait_ready(timeout=self._wait_s)
      #flush buffer to make remaining ids signed
      for bucket_id in range (self._client2multiserver):
        cur_bucket_id = self._initial_bucket + bucket_id
        log.info("flush buffer for bucket {}.".format(cur_bucket_id))
        if self._request_buf[bucket_id]:
          now_bucket_id = self._initial_bucket + bucket_id
          request_ids = list(self._request_buf[bucket_id].keys())
          signed_request_ids = self._rsa_signer[bucket_id].sign_func(request_ids, self._client, now_bucket_id)
          for k, sk in zip(request_ids, signed_request_ids):
            self._sample_store[bucket_id].put(sk, self._request_buf[bucket_id][k])
        self._request_buf[bucket_id].clear()

        #fetch signed ids from server to get join results.
        log.info("begin to join bucket {}.".format(cur_bucket_id))
        batch_cnt = 0
        hit_cnt = 0
        while True:
          finished, real_batch_size, block_id, data = self._client.acquire_server_data(bucket_id=cur_bucket_id)
          if finished:
            break
          existance = self._sample_store[bucket_id].exists(data)

          tmp_res = utils.gather_res(data, existance)
          batch_cnt += 1
          hit_cnt +=  len(existance)
          send_ok = self._client.send_server_res_data(tmp_res, block_id, bucket_id=cur_bucket_id)
          if send_ok:
            # write sample
            self._client.add_checksum(tmp_res, cur_bucket_id)
            for i in tmp_res:
              if self._inputfile_type == 'tfrecord':
                yield str(cur_bucket_id), self._sample_store[bucket_id].get(i)
              else :
                yield str(cur_bucket_id), self._sample_store[bucket_id].get(i).decode() + '\n'
          else:
            raise RuntimeError('Results send fail!')
          if batch_cnt % 100 == 0:
            log.info("Join server data %d batches."%batch_cnt)
        log.info("bucket {} join finish, batch_cnt {}, hit cnt {}.".format(cur_bucket_id, batch_cnt, hit_cnt))

      res = self._client.finish_join()
      if not res:
        raise ValueError("Join finish error")


class ServerRsaJoinFunc(ServerSortJoinFunc):
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
    super().__init__(job_name, port, bucket_num, cmp_func, sample_store_cls, batch_size, wait_s, inputfile_type, run_mode, db_root_path)
    self._rsa_public_key_bytes = kwargs.get('rsa_public_key_bytes', None)
    self._rsa_private_key_bytes = kwargs.get('rsa_private_key_bytes', None)
    self._rsa_signer = ServerRsaSigner(self._rsa_public_key_bytes, self._rsa_private_key_bytes)

  def open(self, runtime_context: RuntimeContext):
    super().open(runtime_context)
    self._rsa_signer = ServerRsaSigner(self._rsa_public_key_bytes, self._rsa_private_key_bytes)
    data_join_server, rpc_server, k8s_resource_handler = create_data_join_server(
      port=self._port,
      job_name=self._job_name,
      bucket_id=self._subtask_index,
      sample_kv_store=self._sample_store,
      run_mode=self._run_mode,
      use_psi=True,
      signer=self._rsa_signer
    )

    self._data_join_server = data_join_server
    self._rpc_server = rpc_server
    self._k8s_resource_handler = k8s_resource_handler

  def process_element(self, value, ctx: 'ProcessFunction.Context'):
    if self.cnt % 1000 == 0:
      s = self._state.value()
      cur = ctx.timestamp() // 1000 * 1000
      if s is None or cur > s:
        self._state.update(cur)
        ctx.timer_service().register_event_time_timer(cur + self._delay)
    key = self._rsa_signer.sign_func([get_sample_store_key(value[0], value[1])])
    self._sample_store.put(key[0],value[2])
    self.cnt += 1

  def on_timer(self, timestamp: int, ctx: 'KeyedProcessFunction.OnTimerContext'):
    s = self._state.value()
    if timestamp >= s + self._delay:
      #join server and wait
      self._data_join_server._reinit_iter()
      self._data_join_server.set_is_ready(True)
      # server wait for 1h
      log.info("RSA DataJoinServer for bucket {} has been ready, "
               "unique key size: {}, all key size:{}"
               .format(ctx.get_current_key(), self._sample_store.size(), self.cnt))
      self._data_join_server.wait_for_finish(timeout=self._wait_s)
      log.info("RSA DataJoinServer for bucket {} finished! "
               "Begin to write sample".format(ctx.get_current_key()))
      for l in self._data_join_server.get_final_result():
        for i in l:
          if self._inputfile_type == 'tfrecord':
            yield str(self._subtask_index), self._sample_store.get(i)
          else :
            yield str(self._subtask_index), self._sample_store.get(i).decode() + '\n'
      self._sample_store.clear()
      if self._run_mode == RunMode.K8S:
        self._k8s_resouce_handler.delete()
