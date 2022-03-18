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

from functools import cmp_to_key

import mmh3
import uuid
import os
from pyflink.common.typeinfo import Types
from pyflink.datastream import KeySelector
from pyflink.datastream.functions import RuntimeContext, KeyedProcessFunction
from pyflink.datastream.state import ValueStateDescriptor

from xfl.common.common import RunMode
from xfl.common.logger import log
from xfl.data import utils
from xfl.data.psi.rsa_signer import ServerRsaSigner, ClientRsaSigner
from xfl.data.store.sample_kv_store import DictSampleKvStore
from xfl.data.store.level_db_kv_store import LevelDbKvStore
from xfl.data.utils import get_sample_store_key, split_sample_store_key
from xfl.service.data_join_client import create_data_join_client
from xfl.service.data_join_server import create_data_join_server


def get_local_bucket_id(key, local_bucket_num):
  return mmh3.hash(key) % local_bucket_num

class DefaultKeySelector(KeySelector):
  def __init__(self, bucket_num: int = 64, client2multiserver: int = 1):
    self._bucket_num = bucket_num * client2multiserver
    self._client2multiserver = client2multiserver

  def get_key(self, value):
    return (mmh3.hash(value[0]) % self._bucket_num) // self._client2multiserver


def record_cmp(left, right):
  a = split_sample_store_key(left)
  b = split_sample_store_key(right)
  if a[1] < b[1]:
    return -1
  if a[1] > b[1]:
    return 1
  if a[0] < b[0]:
    return -1
  if a[0] > b[0]:
    return 1
  return 0

class ClientJoinFunc(KeyedProcessFunction):
  '''
  base class of Client Join Function
  '''
  def __init__(
          self,
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
          db_root_path : str = '/tmp'):
    pass

class ClientBatchJoinFunc(ClientJoinFunc):
  '''
    this join function does not sort sample in one bucket, so it uses less memory.
  '''
  def __init__(self, job_name: str, peer_host: str, peer_ip: str, peer_port: int, bucket_num: int = 64,
               cmp_func=None, sample_store_cls=None, batch_size: int = 2048, wait_s: int = 1800,
               tls_crt: str = '', client2multiserver: int = 1, inputfile_type: str = 'tfrecord',
               run_mode: RunMode = RunMode.LOCAL, db_root_path: str = ''):
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
    self._state = runtime_context.get_state(ValueStateDescriptor(
      "last_modified_time", Types.LONG()))

    self._subtask_index = runtime_context.get_index_of_this_subtask()
    self._initial_bucket = self._subtask_index * self._client2multiserver
    if self._run_mode == RunMode.K8S:
      if self._tls_crt is None or len(self._tls_crt) == 0:
        raise RuntimeError("tls crt should not be empty in k8s mode client job!")
    self.cnt = [0 for i in range(self._client2multiserver)]
    self.cnt_time = 0

    self.client = create_data_join_client(host=self._peer_host,
                                     ip=self._peer_ip,
                                     port=self._peer_port,
                                     job_name=self._job_name,
                                     bucket_id=self._subtask_index,
                                     run_mode=self._run_mode,
                                     tls_crt=self._tls_crt,
                                     client2multiserver=self._client2multiserver)
    log.info("Client begin to wait...")
    self.client.wait_ready(timeout=self._wait_s)

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
      now_bucket_id = self._initial_bucket + bucket_id
      request_ids = list(self._request_buf[bucket_id].keys())
      existence = self.client.sync_join(request_ids, now_bucket_id)
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
      for bucket_id in range (self._client2multiserver):
        if self._request_buf[bucket_id]:
          now_bucket_id = self._initial_bucket + bucket_id
          request_ids = list(self._request_buf[bucket_id].keys())
          existence = self.client.sync_join(request_ids, now_bucket_id)
          res_ids = utils.gather_res(request_ids, existence=existence)
          for i in res_ids:
            if self._inputfile_type == 'tfrecord':
              yield str(now_bucket_id), self._request_buf[bucket_id].get(i)
            else :
              yield str(now_bucket_id), self._request_buf[bucket_id].get(i).decode() + '\n'
        self._request_buf[bucket_id].clear()
      res = self.client.finish_join()
      if not res:
        raise ValueError("Join finish error")

class ClientSortJoinFunc(ClientJoinFunc):
  def __init__(
          self,
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
          db_root_path: str = '/tmp'):
    self._job_name = job_name
    self._bucket_num = bucket_num
    self._state = None
    self._delay = 10000
    self._cmp_func = cmp_func
    self._sample_store_cls = sample_store_cls
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
    # db root path should be a existing directory
    self._db_root_path = db_root_path

  def open(self, runtime_context: RuntimeContext):
    self._state = runtime_context.get_state(ValueStateDescriptor(
      "last_modified_time", Types.LONG()))
    if self._sample_store_cls is DictSampleKvStore:
      self._sample_store = [DictSampleKvStore() for i in range(self._client2multiserver)]
    elif self._sample_store_cls is LevelDbKvStore:
      db_path='{}-{}-bucket_{}'.format(self._job_name, str(uuid.uuid4())[0:6], self._bucket_num)
      self._sample_store = [LevelDbKvStore(path=os.path.join(self._db_root_path, '{}_{}'.format(db_path, i))) for i in range(self._client2multiserver)]
    else:
      raise RuntimeError("sample_store_cls is not supported by now{}".format(self._sample_store_cls))

    self._subtask_index = runtime_context.get_index_of_this_subtask()
    self._initial_bucket = self._subtask_index * self._client2multiserver
    if self._run_mode == RunMode.K8S:
      if self._tls_crt is None or len(self._tls_crt) == 0:
        raise RuntimeError("tls crt should not be empty in k8s mode client job!")

    self.cnt = [0 for i in range(self._client2multiserver)]
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
    self._sample_store[bucket_id].put(get_sample_store_key(value[0], value[1]),value[2])
    self.cnt[bucket_id] += 1

  def on_timer(self, timestamp: int, ctx: 'KeyedProcessFunction.OnTimerContext'):
    s = self._state.value()
    if timestamp >= s + self._delay:
      client = create_data_join_client(host=self._peer_host,
                                       ip=self._peer_ip,
                                       port=self._peer_port,
                                       job_name=self._job_name,
                                       bucket_id=self._subtask_index,
                                       run_mode=self._run_mode,
                                       tls_crt=self._tls_crt,
                                       client2multiserver=self._client2multiserver)
      client.wait_ready(timeout=self._wait_s)
      for bucket_id in range (self._client2multiserver):
        keys_to_join = sorted(self._sample_store[bucket_id].keys(), key=cmp_to_key(self._cmp_func))
        now_bucket_id = self._initial_bucket + bucket_id
        log.info(
          "Client begin to join, bucket id:{}, all size:{}, unique size:{}, subtask index{}".format(now_bucket_id, self.cnt[bucket_id],
                                                                                  len(keys_to_join), self._subtask_index))
        cur = 0
        while cur < len(keys_to_join):
          end = min(cur + self._batch_size, len(keys_to_join))
          request_ids = keys_to_join[cur:end]
          existence = client.sync_join(request_ids, now_bucket_id)
          res_ids = utils.gather_res(request_ids, existence=existence)
          cur = end
          for i in res_ids:
            if self._inputfile_type == 'tfrecord':
              yield str(now_bucket_id), self._sample_store[bucket_id].get(i)
            else :
              yield str(now_bucket_id), self._sample_store[bucket_id].get(i).decode() + '\n'
          log.info("client sync join bucket {} current idx: {}, all: {}".format(now_bucket_id, cur, len(keys_to_join)))
        self._sample_store[bucket_id].clear()
      res = client.finish_join()
      if not res:
        raise ValueError("Join finish error")


class ClientPsiJoinFunc(ClientSortJoinFunc):
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
      db_root_path='/tmp'):
    #The PSI version will be updated later
    raise NotImplementedError('Method not implemented!')

  def open(self, runtime_context: RuntimeContext):
    raise NotImplementedError('Method not implemented!')

  def on_timer(self, timestamp: int, ctx: 'KeyedProcessFunction.OnTimerContext'):
    raise NotImplementedError('Method not implemented!')


class ServerSortJoinFunc(KeyedProcessFunction):
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
    self._job_name = job_name
    self._bucket_num = bucket_num
    self._state = None
    self._delay = 10000
    self._cmp_func = cmp_func
    self._sample_store_cls = sample_store_cls
    self._port = port
    self._wait_s = wait_s
    self._inputfile_type = inputfile_type
    self._run_mode = run_mode
    self._batch_size = batch_size
    # db root path should be an existing directory
    self._db_root_path = db_root_path

  def open(self, runtime_context: RuntimeContext):
    self._state = runtime_context.get_state(ValueStateDescriptor(
      "last_modified_time", Types.LONG()))

    if self._sample_store_cls is DictSampleKvStore:
      self._sample_store = DictSampleKvStore()
    elif self._sample_store_cls is LevelDbKvStore:
      db_path='{}-{}-bucket_{}'.format(self._job_name, str(uuid.uuid4())[0:6], self._bucket_num)
      self._sample_store = LevelDbKvStore(path=os.path.join(self._db_root_path, db_path))
    else:
      raise RuntimeError("sample_store_cls is not supported by now{}".format(self._sample_store_cls))

    self._subtask_index = runtime_context.get_index_of_this_subtask()
    if self._run_mode == RunMode.LOCAL:
      self._port = self._port + runtime_context.get_index_of_this_subtask()
    self.cnt = 0

  def process_element(self, value, ctx: 'ProcessFunction.Context'):
    if self.cnt % 1000 == 0:
      s = self._state.value()
      cur = ctx.timestamp() // 1000 * 1000
      if s is None or cur > s:
        self._state.update(cur)
        ctx.timer_service().register_event_time_timer(cur + self._delay)
    assert(ctx.get_current_key() == self._subtask_index)
    self._sample_store.put(get_sample_store_key(value[0], value[1]),
                           value[2])
    self.cnt += 1

  def on_timer(self, timestamp: int, ctx: 'KeyedProcessFunction.OnTimerContext'):
    s = self._state.value()
    if timestamp >= s + self._delay:
      # create join server and wait
      data_join_server, _, k8s_resouce_handler = create_data_join_server(
        port=self._port,
        job_name=self._job_name,
        bucket_id=self._subtask_index,
        sample_kv_store=self._sample_store,
        run_mode=self._run_mode,
      )
      data_join_server.set_is_ready(True)
      # server wait for 1h
      log.info("DataJoinServer for bucket {} has been ready, "
               "unique key size: {}, all key size:{}"
               .format(self._subtask_index, self._sample_store.size(), self.cnt))
      data_join_server.wait_for_finish(timeout=self._wait_s)
      log.info("DataJoinServer for bucket {} finished! "
               "Begin to write sample".format(ctx.get_current_key()))
      for l in data_join_server.get_final_result():
        for i in l:
          if self._inputfile_type == 'tfrecord':
            yield str(self._subtask_index), self._sample_store.get(i)
          else :
            yield str(self._subtask_index), self._sample_store.get(i).decode() + '\n'
      self._sample_store.clear()
      if self._run_mode == RunMode.K8S:
        k8s_resouce_handler.delete()


class ServerPsiJoinFunc(ServerSortJoinFunc):
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
    raise NotImplementedError('Method not implemented!')

  def open(self, runtime_context: RuntimeContext):
    raise NotImplementedError('Method not implemented!')

  def process_element(self, value, ctx: 'ProcessFunction.Context'):
    raise NotImplementedError('Method not implemented!')

  def on_timer(self, timestamp: int, ctx: 'KeyedProcessFunction.OnTimerContext'):
    raise NotImplementedError('Method not implemented!')