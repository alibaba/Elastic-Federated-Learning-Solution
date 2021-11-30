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
from test.local_join.local_data_set import LocalJoinDataset
from xfl.data.local_join.aux_table import AuxTable
from xfl.data.local_join.worker import LocalJoinWorker
from xfl.data.local_join import utils

import tensorflow_io
import tensorflow as tf

class TestLocalDataJoin(unittest.TestCase):
  def setUp(self):
    self.dataset = LocalJoinDataset()
    self.dataset.init_local_join_data_set()
    self.test_output_dir = 'file:///tmp/xfl-test/local_join_output'
  def test_psi_join(self):
    aux_table1 = AuxTable(self.dataset.aux1_path, self.dataset.aux1_key)
    aux_table2 = AuxTable(self.dataset.aux2_path, self.dataset.aux2_key)
    aux_tables = [aux_table1, aux_table2]
    worker = LocalJoinWorker(input_dir=self.dataset.primary_data_path,
                             output_dir=self.test_output_dir,
                             worker_idx=0,
                             worker_num=2,
                             left_keys=['key', 'key'],
                             aux_tables=aux_tables
                             )
    worker.open()
    worker.run()
    worker = LocalJoinWorker(input_dir=self.dataset.primary_data_path,
                             output_dir=self.test_output_dir,
                             worker_idx=1,
                             worker_num=2,
                             left_keys=['key', 'key'],
                             aux_tables=aux_tables
                             )
    worker.open()
    worker.run()
    self._check_output_data()

  def _check_output_data(self):
    files = utils.list_data_file_recursively(self.test_output_dir)
    idx = 0
    for i in range(len(files)):
      path = os.path.join(self.test_output_dir, str(i)+'.rd')
      self.assertTrue(path in files)
      dataset = tf.data.TFRecordDataset(path)
      for raw_record in dataset:
        example = tf.train.Example()
        example.ParseFromString(raw_record.numpy())
        self.assertEqual(example, self.dataset.ans[idx])
        idx+=1
    self.assertEqual(idx, len(self.dataset.ans))

if __name__ == '__main__':
  unittest.main(verbosity=1)
