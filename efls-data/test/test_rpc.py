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

import unittest
import os
from xfl.service import create_data_join_client, create_data_join_server
from xfl.common.common import RunMode
import multiprocessing as mp
from xfl.data.store import DictSampleKvStore
from xfl.data.psi.ecc_signer import EccSigner
from xfl.common.logger import log
from xfl.data import utils
import random
from xfl.service.nginx import Nginx



def prepare_sample_data():
  #prepare two datasets whose intersection is about 50%.
  DATA_SIZE=10000
  ALL_SIZE=int(DATA_SIZE/2*3)
  raw_data = []
  for i in range(ALL_SIZE):
    raw_data.append(os.urandom(32))
  cli_store = {}
  ser_store = {}
  for i in range(DATA_SIZE):
    ser_store[raw_data[i]]=os.urandom(128)
  random.shuffle(raw_data)
  for i in range(DATA_SIZE):
    cli_store[raw_data[i]]=os.urandom(128)
  return ser_store, cli_store

def run_ecdh_server(store):
  new_store = DictSampleKvStore()
  signer = EccSigner()
  for k in iter(store):
    new_store.put(signer.sign_hash(k), store.get(k))
  data_join_server, rpc_server, _ = create_data_join_server(
      bucket_id=0,
      port=50051,
      job_name='efls-test-service',
      run_mode=RunMode.LOCAL,
      sample_kv_store=new_store,
      use_psi=True,
      signer=signer,
      psi_server_type='ecdh',
      ecdh_id_map=DictSampleKvStore())

  data_join_server.set_is_ready(True)
  data_join_server.wait_for_finish(timeout=3600)


def run_ecdh_client(store):
  client = create_data_join_client(
      host='localhost',
      ip=None,
      #nginx port
      port=80,
      job_name='efls-test-service',
      bucket_id=0,
      run_mode=RunMode.LOCAL,
      tls_crt=None,
      client2multiserver=1
      )
  client.wait_ready(timeout=3600)
  signer = EccSigner()
  item_cnt = 0
  while True:
    finished, real_batch_size, block_id, data = client.acquire_server_data(bucket_id=0)
    if finished:
      break
    item_cnt += real_batch_size
    signed_data = [signer.sign(i) for i in data]
    send_ok = client.send_server_signed_data(signed_data, block_id, bucket_id=0)
    log.info('help server sign data {}, size {}, all size {}'.format(block_id, real_batch_size, item_cnt))
    assert send_ok is True
  log.info("Step1: Sign server data ok! total server data item num: %d"%item_cnt)
  log.info("Step2: Begin to join data..")

  buf = []
  batch_size = 2048
  hit = 0
  cnt = 0
  for k in iter(store):
    buf.append(signer.sign_hash(k))
    if len(buf) >= batch_size:
      existence = client.sync_join(buf, 0)
      res_ids = utils.gather_res(buf, existence=existence)
      hit += sum(existence)
      cnt += len(buf)
      log.info('try to join data, hit size {}, all size{}'.format(hit, cnt))
      buf.clear()
  if buf:
    existence = client.sync_join(buf, 0)
    res_ids = utils.gather_res(buf, existence=existence)
    hit += sum(existence)
    buf.clear()
  log.info("hit size: %d"%hit)
  client.finish_join()

class TestRsaPsi(unittest.TestCase):
  def setUp(self):
    nginx = Nginx('efls-test-service', 1)
    nginx.stop()
    nginx.dumps('/tmp/efls_nginx_test.conf')
    nginx.start('/tmp/efls_nginx_test.conf')
  def test_ecdh_cs(self):
    s1, s2 = prepare_sample_data()
    ser_process = mp.Process(name='server', target=run_ecdh_server, daemon=True, args=(s1,))
    cli_process = mp.Process(name='client', target=run_ecdh_client, daemon=True, args=(s2,))
    ser_process.start()
    cli_process.start()
    ser_process.join()
    cli_process.join()

if __name__ == '__main__':
  unittest.main(verbosity=1)
