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
from xfl.data.psi.rsa_signer import ServerRsaSigner
from xfl.data.store.sample_kv_store import SampleKvStore
from xfl.k8s.k8s_client import K8sClient
from xfl.k8s.k8s_resource import create_data_join_service, create_data_join_ingress, \
  release_data_join_ingress, release_data_join_service


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

  def IsReady(self, request: data_join_pb2.BucketIdRequest, context) -> common_pb2.Status:
    if self._ready:
      return common_pb2.Status(code=common_pb2.OK, message='')
    else:
      return common_pb2.Status(code=common_pb2.NOT_READY, message='not_ready')

  def FinishJoin(self, request: data_join_pb2.FinishJoinRequest, context) -> common_pb2.Status:
    if self._finished.isSet():
      return common_pb2.Status(code=common_pb2.INTERNAL, message='Server has finished!')

    for i in self._joined_res:
      self._check_sum.add_list(i)

    if self._check_sum.get_check_sum() != request.check_sum:
      log.error("CheckSum Error, request :%d, Server :%d", request.check_sum, self._check_sum.get_check_sum())
      return common_pb2.Status(code=common_pb2.INTERNAL, message='CheckSumError, Join Failed')
    log.info("CheckSum check ok! Finish Server for bucket:{} !".format(self._bucket_id))
    self._finished.set()
    return common_pb2.Status(code=common_pb2.OK, message='')

  def SyncJoin(self, request: data_join_pb2.JoinRequest, context) -> data_join_pb2.JoinResponse:
    if not self._ready:
      return self._join_response(common_pb2.NOT_READY, '', [])

    else:
      if self._bucket_id != request.bucket_id:
        return self._join_response(common_pb2.INVALID_ARGUMENT, '', [])
      res = self._sample_kv_store.exists(request.ids)
      with self._joined_res_lock:
        self._joined_res.append(utils.gather_res(request.ids, res))
      return self._join_response(common_pb2.OK, '', res)

  def AsyncJoin(self, request: data_join_pb2.AsyncJoinRequest, context) -> data_join_pb2.JoinResponse:
    raise NotImplementedError('Method not implemented!')

  def GetBloomFilter(self, request, context):
    raise NotImplementedError('Method not implemented!')


class PsiDataJoinServer(DataJoinServer):
  def __init__(self, sample_kv_store: SampleKvStore, bucket_id, rsa_signer, is_async_join=False, ):
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
    log.info("Register k8s serivce and ingress for job:{}, bucket:{}, pod:{}"
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
    # ingress register
    create_data_join_ingress(
      client=self.kcli,
      app_name=self.job_name,
      bucket_id=self.bucket_id,
    )

  def delete(self):
    if self.kcli == None:
      raise RuntimeError("K8sResourceHandler `delete()` should be called after `create()`")
    release_data_join_ingress(
      client=self.kcli,
      app_name=self.job_name,
      bucket_id=self.bucket_id
    )
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
                            ):
  rpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
  if use_psi:
    data_join_server = PsiDataJoinServer(sample_kv_store=sample_kv_store, bucket_id=bucket_id,
                                         rsa_signer=signer)
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
