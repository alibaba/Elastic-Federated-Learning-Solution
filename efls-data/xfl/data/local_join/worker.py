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
from typing import List
import tensorflow_io
import tensorflow as tf
from tensorflow.python.platform import gfile
from xfl.data.local_join.aux_table import AuxTable
from xfl.data.local_join import utils
from xfl.data.local_join.sharding import FileSharding
from xfl.common.logger import log
tf.compat.v1.enable_eager_execution()

class LocalJoinWorker(object):
  def __init__(self,
               input_dir: str,
               output_dir: str,
               worker_idx: int,
               worker_num: int,
               left_keys: list,
               aux_tables: List[AuxTable],
               ):
    self.input_dir = input_dir
    self.output_dir = output_dir
    self.aux_tables = aux_tables
    self.worker_idx = worker_idx
    self.worker_num = worker_num
    self.left_keys = left_keys
    self.shard_to_process = []
    if not len(left_keys) == len(aux_tables):
      raise RuntimeError('left_keys size must be equal with aux_table size {}, got {}'
                         .format(len(aux_tables), len(left_keys)))
  def open(self):
    utils.assert_valid_dir(path=self.input_dir)
    if not gfile.Exists(self.output_dir):
      gfile.MakeDirs(self.output_dir)
    for t in self.aux_tables:
      t.open()
    sharding = FileSharding()
    self.shard_to_process = sharding.shard(worker_idx=self.worker_idx,
                                           worker_num=self.worker_num,
                                           input_path=self.input_dir,
                                           output_path=self.output_dir)
    log.info("worker {} will process {} shards...".format(self.worker_idx, len(self.shard_to_process)))

  def run(self):
    for shard in self.shard_to_process:
      log.info("read file {}, and begin writing to file {}.".format(shard[0], shard[1]))
      if not gfile.Exists(shard[0]):
        raise RuntimeError("file {} does not exist, please check input data.".format(shard[0]))
      if not gfile.Exists(os.path.dirname((shard[1]))):
        gfile.MakeDirs(os.path.dirname(shard[1]))
      writer = tf.io.TFRecordWriter(shard[1])
      dataset = tf.data.TFRecordDataset(shard[0])
      for raw_record in dataset:
        example = tf.train.Example()
        example.ParseFromString(raw_record.numpy())
        for k, t in zip(self.left_keys, self.aux_tables):
          if k not in example.features.feature:
            raise RuntimeError("key col {} is not in input record, please check your data.".format(k))
          if not example.features.feature[k].WhichOneof('kind')=='bytes_list':
            raise RuntimeError("key col {} type must be bytes_list, but got {}".format(k, example.features.feature[k].WhichOneof('kind')))
          if not len(example.features.feature[k].bytes_list.value) == 1:
            raise RuntimeError("key col {} length must be 1, but got {}".format(k, len(example.features.feature[k].bytes_list.value)))
          example_right_str = t.get(example.features.feature[k].bytes_list.value[0])
          if example_right_str is not None:
            example_right = tf.train.Example()
            example_right.ParseFromString(example_right_str)
            example.MergeFrom(example_right)
        writer.write(example.SerializeToString())
      writer.close()
      log.info("write to file {} end.".format(shard[1]))
