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

from xfl.data.store.level_db_kv_store import LevelDbKvStore

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
    store.clear()
    store = LevelDbKvStore('/tmp/xfl_test_leveldb')
    self.assertEqual(store.exists([b'a',b'd',b'c']), [False, False, False])
    store.clear()

if __name__ == '__main__':
  unittest.main(verbosity=1)
