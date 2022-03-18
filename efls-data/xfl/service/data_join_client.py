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

import time
import json
import grpc
from google.protobuf.empty_pb2 import Empty

from proto import data_join_pb2_grpc, data_join_pb2, common_pb2
from proto.data_join_pb2 import BucketIdRequest
from xfl.data.check_sum import CheckSum
from xfl.data import utils
from xfl.common.common import RunMode
from xfl.common.decorator import retry_fn
from xfl.common.logger import log
from xfl.service.proxy import get_insecure_channel

class DataJoinClient(object):
  def __init__(self,
               host: str,
               ip: str,
               port: int,
               job_name: str,
               bucket_id: int,
               run_mode: RunMode = RunMode.LOCAL,
               tls_crt: str = '',
               client2multiserver: int = 1):

    log.info("Client run mode: {}".format(run_mode))
    log.info("Start a DataJoinClient at host:{}, ip:{}, port:{}".format(host, ip, port))
    self._job_name = job_name
    self._init_bucket_id = bucket_id * client2multiserver
    self._client2multiserver = client2multiserver
    self._checksumlist = [CheckSum() for i in range(client2multiserver)]
    self._metadata = (("servicename", '{}-{}'.format(job_name, self._init_bucket_id)), ("app", job_name))
    #Grpc requests will be forwarded through servicename in part configuration-snippet of nginx-ingress
    log.info("metadata:{}".format(self._metadata))

    service_config_json = json.dumps({
      "methodConfig": [{
        "name": [
          {
            "service": "xfl.DataJoinService",
            "method": "IsReady"
          },
          {
            "service": "xfl.DataJoinService",
            "method": "SyncJoin"
          },
          {
            "service": "xfl.DataJoinService",
            "method": "FinishJoin"
          },
          {
            "service": "xfl.DataJoinService",
            "method": "AcquireServerData"
          },
          {
            "service": "xfl.DataJoinService",
            "method": "SendServerSignedData"
          }
        ],
        "retryPolicy": {
          "maxAttempts": 5,
          "initialBackoff": "0.2s",
          "maxBackoff": "10s",
          "backoffMultiplier": 2,
          "retryableStatusCodes": ["UNAVAILABLE"],
        },
      }]
    })
    if run_mode == RunMode.LOCAL:
      address = "{}:{}".format(host, port)
      self._channel = get_insecure_channel(address,
                                           options=[('grpc.max_send_message_length', 2 ** 31 - 1),
                                                    ('grpc.max_receive_message_length', 2 ** 31 - 1),
                                                    ("grpc.enable_retries", 1),
                                                    ("grpc.service_config", service_config_json)])
    elif run_mode == RunMode.K8S:
      credentials = grpc.ssl_channel_credentials(root_certificates=tls_crt)
      address = "{}:{}".format(ip, port)
      log.info("Data Join Client TLS host: {}".format(host))
      self._channel = grpc.secure_channel(address, credentials,
                                          options=(('grpc.ssl_target_name_override', host),
                                                   ('grpc.max_send_message_length', 2 ** 31 - 1),
                                                   ('grpc.max_receive_message_length', 2 ** 31 - 1),
                                                   ("grpc.enable_retries", 1),
                                                   ("grpc.service_config", service_config_json)))
    self._stub = data_join_pb2_grpc.DataJoinServiceStub(self._channel)

  def get_stub(self):
    return self._stub

  def wait_ready(self, timeout=None):
    bucket_id = self._init_bucket_id
    for t in range(self._client2multiserver):
      cnt = 0
      while True:
        try:
          log.info("client waiting ...")
          res = self._stub.IsReady(data_join_pb2.BucketIdRequest(bucket_id=bucket_id),
                                  metadata=(("servicename", '{}-{}'.format(self._job_name, bucket_id)), ("app", self._job_name)))
          if res.code == common_pb2.OK:
            break
          log.info("Client wait not ready:%s", res.message)
        except Exception as e:
          log.info("Client wait exception:%s", str(e))
        finally:
          cnt += 1
          time.sleep(1)

          if timeout is not None and cnt > timeout:
            raise InterruptedError("Client wait server ready time out!")
      bucket_id += 1
    return True

  @retry_fn(retry_times=10, needed_exceptions=[grpc.RpcError], retry_interval=0.2)
  def finish_join(self):
    bucket_id = self._init_bucket_id
    for t in range(self._client2multiserver):
      res = self._stub.FinishJoin(data_join_pb2.FinishJoinRequest(bucket_id=bucket_id, check_sum=self._checksumlist[t].get_check_sum()),
                                  metadata=(("servicename", '{}-{}'.format(self._job_name, bucket_id)), ("app", self._job_name)))
      if res.code != common_pb2.OK:
        log.error("Finish Join Error:%s", str(res))
        return False
      else :
        log.info("End join bucket {}, checkSum:{}".format(bucket_id, self._checksumlist[t].get_check_sum()))
      bucket_id += 1
    return True

  @retry_fn(retry_times=10, needed_exceptions=[grpc.RpcError], retry_interval=0.2)
  def sync_join(self, request_ids, bucket_id):
    join_res = None
    res = self._stub.SyncJoin(
      data_join_pb2.JoinRequest(ids=request_ids, bucket_id=bucket_id),
      metadata=(("servicename", '{}-{}'.format(self._job_name, bucket_id)), ("app", self._job_name))
    )

    if res.status.code == common_pb2.OK:
      join_res = list(res.join_res)
      res_ids = utils.gather_res(request_ids, existence=join_res)
      self._checksumlist[bucket_id - self._init_bucket_id].add_list(res_ids)
    else:
      raise RuntimeError('Sync Join Error:%s' % str(res))
    return join_res

  @retry_fn(retry_times=10, needed_exceptions=[grpc.RpcError], retry_interval=0.2)
  def sign_blinded_ids_from_server(self, request_ids, bucket_id):
    res = self._stub.PsiSign(
      data_join_pb2.PsiSignRequest(ids=request_ids),
      metadata=(("servicename", '{}-{}'.format(self._job_name, bucket_id)), ("app", self._job_name))
    )
    if res.status.code == common_pb2.OK:
      return list(res.signed_ids)
    else:
      log.error("Psi Sign Error:%s", str(res))
      raise RuntimeError('Psi Sign Error:%s' % str(res))

  @retry_fn(retry_times=10, needed_exceptions=[grpc.RpcError], retry_interval=0.2)
  def request_public_key_from_server(self, bucket_id):
    res = self._stub.GetRsaPublicKey(Empty(),
                                     metadata=(("servicename", '{}-{}'.format(self._job_name, bucket_id)), ("app", self._job_name)))
    if res.status.code == common_pb2.OK:
      return res.key
    else:
      log.error("Get public key Error:%s", str(res))
      raise RuntimeError('Get public key Error:%s' % str(res))


  @retry_fn(retry_times=10, needed_exceptions=[grpc.RpcError], retry_interval=0.2)
  def acquire_server_data(self, bucket_id, timeout_s = 10):
    options = data_join_pb2.RequestServerOptions(timeout_s=timeout_s)
    res = self._stub.AcquireServerData(options,
                                     metadata=(("servicename", '{}-{}'.format(self._job_name, bucket_id)), ("app", self._job_name)))
    if res.status.code != common_pb2.OK:
      raise RuntimeError('acquire_server_data error: %s'%res.status.message)
    if res.is_finished:
      return True, 0, 0, []
    return False, res.real_batch_size, res.block_id, res.signed_ids

  @retry_fn(retry_times=10, needed_exceptions=[grpc.RpcError], retry_interval=0.2)
  def send_server_signed_data(self, data, block_id, bucket_id):
    data_block = data_join_pb2.DataBlock(block_id=block_id, data=data)
    status = self._stub.SendServerSignedData(data_block,
                                     metadata=(("servicename", '{}-{}'.format(self._job_name, bucket_id)), ("app", self._job_name)))
    if status.code != common_pb2.OK:
      raise RuntimeError('send_server_signed_data error:%s'%status.message)
    return True

def create_data_join_client(host,
                            ip,
                            port,
                            job_name,
                            bucket_id,
                            run_mode,
                            tls_crt,
                            client2multiserver,
                            ):
  client = DataJoinClient(host=host, ip=ip, port=port, job_name=job_name, bucket_id=bucket_id,
                          run_mode=run_mode, tls_crt=tls_crt, client2multiserver=client2multiserver)
  return client
