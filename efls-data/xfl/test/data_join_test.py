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
import time
import unittest
from concurrent import futures

import grpc

from proto import data_join_pb2_grpc
from xfl.common.logger import log
from xfl.data import utils
from xfl.data.check_sum import CheckSum
from xfl.data.store import DictSampleKvStore
from xfl.service.data_join_client import DataJoinClient
from xfl.service.data_join_server import DataJoinServer


def start_server():
  rpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
  sample_kv_store = DictSampleKvStore()

  data_join_server = DataJoinServer(sample_kv_store=sample_kv_store, bucket_id=0)
  data_join_pb2_grpc.add_DataJoinServiceServicer_to_server(data_join_server, rpc_server)
  rpc_server.add_insecure_port('[::]:50051')
  rpc_server.start()
  log.info("rpc server start")

  sample_kv_store.put(b'123', 111)
  log.info("add data 123...")
  time.sleep(2)
  sample_kv_store.put(b'456', 222)

  log.info("add data 456...")
  time.sleep(2)

  data_join_server.set_is_ready(True)
  data_join_server.wait_for_finish()
  log.info("Server finished")
  rpc_server.stop(grace=None)
  return data_join_server


def start_client():
  client = DataJoinClient(bucket_id=0, address='localhost:50051')
  return client


class TestDemo(unittest.TestCase):
  def setUp(self) -> None:
    log.info("Set up")
    self._pid = os.fork()
    if self._pid == 0:
      log.info("Start server in child")
      self._server = start_server()

    else:
      time.sleep(1)
      log.info("Start Client in child")
      self._client = start_client()

  def tearDown(self) -> None:
    if self._pid == 0:
      log.info("Server tear down")
    else:
      log.info("Client tear down")

  def test_sync_join(self):
    if self._pid == 0:
      log.info("Server No Test")
      res = self._server.get_final_result()
      self.assertEqual(res, [[b'123'], [b'456'], [b'456']])
    else:
      self.assertTrue(self._client.wait_ready())

      _check_sum = CheckSum()
      log.info("Client wait ready ok!!!")
      input1 = [b'123', b'none']
      res = self._client.sync_join(input1)
      self.assertEqual(res, [True, False])

      _check_sum.add_list(utils.gather_res(input1, res))

      input2 = [b'none', b'456']
      res = self._client.sync_join(input2)
      self.assertEqual(res, [False, True])

      _check_sum.add_list(utils.gather_res(input2, res))
      time.sleep(1)
      res = self._client.sync_join(input2)
      self.assertEqual(res, [False, True])
      _check_sum.add_list(utils.gather_res(input2, res))

      log.info("Client send Finish Join!")
      self.assertTrue(self._client.finish_join(check_sum=_check_sum.get_check_sum()))


if __name__ == '__main__':
  unittest.main(verbosity=1)
