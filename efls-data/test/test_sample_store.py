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
import time
import shutil

from xfl.data.store import LevelDbKvStore, DictSampleKvStore

def get_dir_size(path):
  total = 0
  with os.scandir(path) as it:
    for entry in it:
      if entry.is_file():
        total += entry.stat().st_size
      elif entry.is_dir():
        total += get_dir_size(entry.path)
  return total
def test_level_db_store_speed(write_buffer_size_mb = 4):
  path = '/tmp/xfl_test_leveldb_speed'
  if os.path.exists(path):
    shutil.rmtree(path)
  MB = 1024*1024
  write_buffer_size_mb = write_buffer_size_mb
  store = LevelDbKvStore(path, write_buffer_size = write_buffer_size_mb*MB, max_file_size=8*MB)
  begin = time.time()
  data_size = 10000
  for i in range(data_size):
    store.put(os.urandom(32), os.urandom(10000))
  end = time.time()
  db_size = get_dir_size(path)

  print ('')
  print('========results with {} mb wirte buffer size======='.format(write_buffer_size_mb))
  print('key size 32bytes, value size 10K bytes, data_size items')
  print('dir size: %.2f MB'%(db_size/MB))
  print('compress ratio %.2f'%(db_size/10032/data_size))
  print('wirte qps: %.2f'%(data_size/(end-begin)))

  begin = time.time()
  for i in range(1000000):
    store.get(os.urandom(32))
  end = time.time()
  print('get qps: %.2f'%(data_size/(end-begin)))

  begin = time.time()
  for i in iter(store):
    i+b'a'
  end = time.time()
  print('iterator qps: %.2f'%(data_size/(end-begin)))
  print('===================================================')
  store.clear()

class TestSampleStore(unittest.TestCase):
  def test_level_db_store(self):
    store = LevelDbKvStore('/tmp/xfl_test_leveldb')
    store.put(b'a', b'a')
    store.put(b'b', b'b')
    store.put(b'c', b'a')
    self.assertEqual(store.get(b'a'), b'a')
    self.assertEqual(store.exists([b'a',b'd',b'c']), [True, False, True])
    self.assertEqual(store.size(), 3)
    self.assertEqual(store.keys(), [b'a',b'b',b'c'])
    it = iter(store)
    self.assertEqual(list(it), [b'a',b'b',b'c'])
    store.put(b'a', b'c')
    self.assertEqual(store.get(b'a'), b'c')
    store.clear()
    store = LevelDbKvStore('/tmp/xfl_test_leveldb')
    self.assertEqual(store.exists([b'a',b'd',b'c']), [False, False, False])
    store.clear()

  def test_dict_sample_kv_store(self):
    store = DictSampleKvStore()
    store.put(b'a', b'a')
    store.put(b'b', b'b')
    store.put(b'c', b'a')
    self.assertEqual(store.get(b'a'), b'a')
    self.assertEqual(store.exists([b'a',b'd',b'c']), [True, False, True])
    self.assertEqual(store.size(), 3)
    self.assertEqual(store.keys(), [b'a',b'b',b'c'])
    store.put(b'a', b'c')
    self.assertEqual(store.get(b'a'), b'c')
    store.clear()

#  def test_speed(self):
#    buf_sizes = [4,16,64,128]
#    for v in buf_sizes:
#      test_level_db_store_speed(write_buffer_size_mb=v)

if __name__ == '__main__':
  unittest.main(verbosity=1)
