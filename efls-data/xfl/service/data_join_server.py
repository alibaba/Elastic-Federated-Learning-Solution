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
import os
import threading
from concurrent import futures

import grpc

from proto import data_join_pb2, data_join_pb2_grpc, common_pb2
from xfl.common.common import RunMode
from xfl.common.logger import log
from xfl.data import utils
from xfl.data.check_sum import CheckSum
from xfl.data.store.sample_kv_store import SampleKvStore
from xfl.k8s.k8s_client import K8sClient
from xfl.k8s.k8s_resource import create_data_join_service, release_data_join_service


class DataJoinServer(data_join_pb2_grpc.DataJoinServiceServicer):
  def __init__(self, sample_kv_store: SampleKvStore, bucket_id, is_async_join=False):
    self._finished = threading.Event()
    self._bucket_id = bucket_id
    self._ready = False
    self._is_async_join = is_async_join
    self._joined_res_lock = threading.Lock()
    self._joined_res = []
    self._check_sum = CheckSum(0)
    self._sample_kv_store = sample_kv_store
    self._request_cnt = 0
    self._hit_cnt = 0
    self._all_cnt = 0
    assert isinstance(self._sample_kv_store, SampleKvStore)

  @staticmethod
  def _join_response(code, message: str, res: list) -> data_join_pb2.JoinResponse:
    return data_join_pb2.JoinResponse(status=common_pb2.Status(code=code, message=message),
                                      join_res=res)

  def set_is_ready(self, value: bool):
    self._ready = value

  def get_is_ready(self):
    return self._ready

  def wait_for_finish(self, timeout: float = None):
    log.info("Server wait for finish")
    self._finished.wait(timeout=timeout)

  def get_final_result(self):
    return self._joined_res

  def print_result_statistic(self):
    log.info("Join result, reuqest cnt: {}, ids cnt: {}, ids hit cnt: {}"
             .format(self._request_cnt, self._all_cnt, self._hit_cnt))

  def IsReady(self, request: data_join_pb2.BucketIdRequest, context) -> common_pb2.Status:
    if self._ready:
      return common_pb2.Status(code=common_pb2.OK, message='')
    else:
      return common_pb2.Status(code=common_pb2.NOT_READY, message='not_ready')

  def FinishJoin(self, request: data_join_pb2.FinishJoinRequest, context) -> common_pb2.Status:
    if self._finished.isSet():
      return common_pb2.Status(code=common_pb2.INTERNAL, message='Server has finished!')

    if self._check_sum.get_check_sum() != request.check_sum:
      log.error("CheckSum Error, request :%d, Server :%d", request.check_sum, self._check_sum.get_check_sum())
      return common_pb2.Status(code=common_pb2.INTERNAL, message='CheckSumError, Join Failed')
    log.info("CheckSum check ok, value is {}. Finish Server for bucket:{} !".format(request.check_sum, self._bucket_id))
    self.print_result_statistic()
    self._finished.set()
    return common_pb2.Status(code=common_pb2.OK, message='')

  def SyncJoin(self, request: data_join_pb2.JoinRequest, context) -> data_join_pb2.JoinResponse:
    if not self._ready:
      return self._join_response(common_pb2.NOT_READY, '', [])

    else:
      self._request_cnt += 1
      if self._bucket_id != request.bucket_id:
        return self._join_response(common_pb2.INVALID_ARGUMENT,
            'bucket id not match, expect {}, got {}'.format(self._bucket_id, request.bucket_id), [])
      res = self._sample_kv_store.exists(request.ids)
      self._all_cnt += len(request.ids)
      self._hit_cnt += sum(res)
      with self._joined_res_lock:
        tmp_res = utils.gather_res(request.ids, res)
        self._joined_res.append(tmp_res)
        self._check_sum.add_list(tmp_res)
      return self._join_response(common_pb2.OK, '', res)

  def AsyncJoin(self, request: data_join_pb2.AsyncJoinRequest, context) -> data_join_pb2.JoinResponse:
    raise NotImplementedError('Method not implemented!')

  def GetBloomFilter(self, request, context):
    raise NotImplementedError('Method not implemented!')


class PsiDataJoinServer(DataJoinServer):
  def __init__(self, sample_kv_store: SampleKvStore, bucket_id, rsa_signer, is_async_join=False):
    super().__init__(sample_kv_store, bucket_id, is_async_join)
    assert rsa_signer is not None, "rsa signer should not be None!"
    self.rsa_signer_ = rsa_signer

  def GetRsaPublicKey(self, request, context):
    return data_join_pb2.RsaKey(status=common_pb2.Status(code=common_pb2.OK, message=''),
                                key=self.rsa_signer_.get_public_key_bytes())

  def PsiSign(self, request, context):
    if not self._ready:
      return data_join_pb2.PsiSignResponse(status=common_pb2.Status(code=common_pb2.NOT_READY, message=''),
                                           signed_ids=[])
    else:
      signed_ids = self.rsa_signer_.sign_blinded_ids_from_client(request.ids)
      return data_join_pb2.PsiSignResponse(status=common_pb2.Status(code=common_pb2.OK, message=''),
                                           signed_ids=signed_ids)


class EcdhDataJoinServer(DataJoinServer):
  def __init__(self,
      sample_kv_store: SampleKvStore,
      bucket_id,
      ecc_signer,
      is_async_join=False,
      pending_max_size=1000,
      batch_size=2048,
      signed_id_map: SampleKvStore=None):
    super().__init__(sample_kv_store, bucket_id, is_async_join)
    assert ecc_signer is not None, "ecc signer should not be None!"
    self._ecc_signer = ecc_signer
    self._cli_sign_lock = threading.Lock()
    self._pending_max_size = 1000
    self._data_pending_buffer = {}
    self._batch_size = batch_size
    self._data_it = iter(sample_kv_store)
    self._block_id = 0
    self._server_data_exhausted = False
    self._signed_id_map = signed_id_map


  def _fetch_a_batch(self):
    batch = []
    try:
      for i in range(self._batch_size):
        batch.append(next(self._data_it))
    except StopIteration:
      pass
    if batch:
      self._block_id += 1
      return self._block_id, batch
    else:
      return None, None

  def _all_server_data_ready(self):
    return self._server_data_exhausted and len(self._data_pending_buffer)==0

  def AcquireServerData(self, option: data_join_pb2.RequestServerOptions, context) -> data_join_pb2.RequestServerRes:
    block_id, batch = self._fetch_a_batch()
    if block_id:
      with self._cli_sign_lock:
        self._data_pending_buffer[block_id] = batch
      return data_join_pb2.RequestServerRes(status=common_pb2.Status(code=common_pb2.OK, message=''),
            signed_ids=batch,
            block_id=block_id,
            real_batch_size=len(batch),
            is_finished=False)
    else:
      self._server_data_exhausted = True
      return data_join_pb2.RequestServerRes(status=common_pb2.Status(code=common_pb2.OK, message=''),
            signed_ids=[],
            block_id=0,
            real_batch_size=0,
            is_finished=True)

  def SendServerSignedData(self, data_block: data_join_pb2.DataBlock, context) -> common_pb2.Status:
    block_id = data_block.block_id
    signed_ids = data_block.data
    if block_id not in self._data_pending_buffer:
      return common_pb2.Status(code=common_pb2.INVALID_ARGUMENT, message='unexpected block_id: %d'%block_id)
    if len(signed_ids) != len(self._data_pending_buffer[block_id]):
      return common_pb2.Status(code=common_pb2.INVALID_ARGUMENT,
          message='signed data length error, expected %d, got %d'%(len(self._data_pending_buffer),len(signed_ids)))
    #update sample store keys
    buf = self._data_pending_buffer[block_id]
    for i,k in enumerate(signed_ids):
      self._signed_id_map.put(k,buf[i])
    with self._cli_sign_lock:
      del self._data_pending_buffer[block_id]
    return common_pb2.Status(code=common_pb2.OK)

  def SyncJoin(self, request: data_join_pb2.JoinRequest, context) -> data_join_pb2.JoinResponse:
    if not self._ready:
      return self._join_response(common_pb2.NOT_READY, '', [])

    elif not self._all_server_data_ready:
      return self._join_response(common_pb2.NOT_READY, 'there is still server data not signed by client', [])
    else:
      self._request_cnt += 1
      if self._bucket_id != request.bucket_id:
        return self._join_response(common_pb2.INVALID_ARGUMENT,
            'bucket id not match, expect {}, got {}'.format(self._bucket_id, request.bucket_id), [])
      #in ecdh, ids should be signed before Join
      signed_ids = [self._ecc_signer.sign(x) for x in request.ids]
      res = self._signed_id_map.exists(signed_ids)
      self._all_cnt += len(request.ids)
      self._hit_cnt += sum(res)
      with self._joined_res_lock:
        self._joined_res.append(utils.gather_res(signed_ids, res))
        self._check_sum.add_list(utils.gather_res(request.ids, res))
      return self._join_response(common_pb2.OK, '', res)

class K8sResourceHandler(object):

  def __init__(self,
               job_name,
               bucket_id,
               port,
               config_path=None) -> None:
    self.job_name = job_name
    self.bucket_id = bucket_id
    self.port = port
    self.kcli = None
    self.config_path = config_path

  def create(self):
    self.pod_name = os.environ["HOSTNAME"]
    log.info("Register k8s serivce for job:{}, bucket:{}, pod:{}"
             .format(self.job_name, self.bucket_id, self.pod_name))
    self.kcli = K8sClient()
    self.kcli.init(config_path=self.config_path)
    pod = self.kcli.get_pod(self.pod_name)
    assert pod is not None, 'pod:{} existence error!'.format(self.pod_name)
    self.pod_uid = pod.metadata.uid
    # add label for current pod
    self.kcli.update_pod_labels(self.pod_name, {"xfl-app": self.job_name, "bucket-id": str(self.bucket_id)})
    # service register
    create_data_join_service(
      client=self.kcli,
      app_name=self.job_name,
      bucket_id=self.bucket_id,
      target_port=self.port
    )

  def delete(self):
    if self.kcli == None:
      raise RuntimeError("K8sResourceHandler `delete()` should be called after `create()`")
    release_data_join_service(
      client=self.kcli,
      app_name=self.job_name,
      bucket_id=self.bucket_id
    )
    self.kcli.close()


def create_data_join_server(bucket_id,
                            port: int,
                            job_name: str,
                            run_mode: RunMode,
                            sample_kv_store: SampleKvStore,
                            use_psi=False,
                            signer=None,
                            psi_server_type='rsa', #rsa or ecdh
                            ecdh_id_map: SampleKvStore = None
                            ):
  rpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
  if use_psi:
    if psi_server_type == 'rsa':
      data_join_server = PsiDataJoinServer(
          sample_kv_store=sample_kv_store,
          bucket_id=bucket_id,
          rsa_signer=signer)
    elif psi_server_type == 'ecdh':
      data_join_server = EcdhDataJoinServer(
          sample_kv_store=sample_kv_store,
          bucket_id=bucket_id,
          ecc_signer=signer,
          signed_id_map=ecdh_id_map)
    else:
      raise RuntimeError('unsupported psi server type: %s'%psi_server_type)
  else:
    data_join_server = DataJoinServer(sample_kv_store=sample_kv_store, bucket_id=bucket_id)

  data_join_pb2_grpc.add_DataJoinServiceServicer_to_server(data_join_server, rpc_server)
  address = '[::]:{}'.format(str(port))
  rpc_server.add_insecure_port(address)
  rpc_server.start()
  log.info("Create Data Join Server Ok... At: {}".format(address))

  k8s_resource_handler = None
  if run_mode == RunMode.K8S:
    k8s_resource_handler = K8sResourceHandler(
      job_name=job_name, bucket_id=bucket_id, port=port)
    k8s_resource_handler.create()
  return data_join_server, rpc_server, k8s_resource_handler
