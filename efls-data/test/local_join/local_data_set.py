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

import random
import tensorflow as tf
import os
from tensorflow.python.platform import gfile
from xfl.common.logger import log


class LocalJoinDataset(object):
  def __init__(self,
               primary_data_path: str = 'file:///tmp/xfl-test/local_join_primary',
               aux1_path: str = 'file:///tmp/xfl-test/local_join_aux1',
               aux2_path: str = 'file:///tmp/xfl-test/local_join_aux2',
               aux1_key: str = 'aux1_key',
               aux2_key: str = 'aux2_key',
               primary_size=60000,
               aux_size=10000,
               file_part_size=4096):
    self.primary_data_path = primary_data_path
    self.aux1_path = aux1_path
    self.aux2_path = aux2_path
    self.primary_size = primary_size
    self.aux_size = aux_size
    self.file_part_size = file_part_size
    self.aux1_key = aux1_key
    self.aux2_key = aux2_key
    self.ans = []

  @staticmethod
  def _bytes_feature(value):
    if isinstance(value, type(tf.constant(0))):
      value = value.numpy()  # BytesList won't unpack a string from an EagerTensor.
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

  @staticmethod
  def _float_feature(value):
    return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))

  @staticmethod
  def _int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))

  def _make_two_col_data(self, size, key_range: int = 1e6, key_col_name="key", value_col_name="value"):
    key_set = set()
    data_list = []
    for i in range(size):
      x, v = random.randint(0, key_range), random.randint(0, key_range)
      # to make dedup data
      while x in key_set:
        x = random.randint(0, key_range)
      key_set.add(x)
      tf_example = tf.train.Example(
        features=tf.train.Features(
          feature={
            key_col_name: self._bytes_feature(x.to_bytes(length=8, byteorder='big', signed=False)),
            value_col_name: self._float_feature(float(v)),
          }
        ))
      data_list.append(tf_example)
    data_list.sort(key=lambda x:self._get_key_from_tfrecord(x, key_col_name))
    return data_list

  def _write_data_list_to_path(self, path, data_list):
    log.info('write test local join data to path: {}, size {}'.
            format(path, len(data_list)))
    if gfile.Exists(path):
      gfile.DeleteRecursively(path)
    gfile.MakeDirs(path)
    cnt_file = 0
    cnt_data = 0
    data_list_size = len(data_list)
    output_file_path = os.path.join(path, str(cnt_file) + '.rd')
    output_file = tf.io.TFRecordWriter(output_file_path)
    for i in range(data_list_size):
      output_file.write(data_list[i].SerializeToString())
      cnt_data += 1
      if cnt_data >= self.file_part_size:
        output_file.close()
        cnt_file += 1
        output_file_path = os.path.join(path, str(cnt_file) + '.rd')
        output_file = tf.io.TFRecordWriter(output_file_path)
        cnt_data = 0


  def _get_data_dict(self, data_list, key_col_name):
    data_dict = {}
    for tf_example in data_list:
      key = self._get_key_from_tfrecord(tf_example, key_col_name)
      data_dict[key] = tf_example
    return data_dict

  @staticmethod
  def _get_key_from_tfrecord(tf_record,  key_col_name):
    return  tf_record.features.feature[key_col_name].bytes_list.value[0]

  def init_local_join_data_set(self):
    log.info('prepare local join data set.')
    log.info('prepare local join parimary data.')
    self._data_primary = self._make_two_col_data(size=self.primary_size)
    log.info('prepare local join aux table1.')
    self._data_aux1 = self._make_two_col_data(size=self.aux_size, key_col_name='aux1_key', value_col_name='aux_1_value')
    log.info('prepare local join aux table2.')
    self._data_aux2 = self._make_two_col_data(size=self.aux_size, key_col_name='aux2_key', value_col_name='aux_2_value')
    self._write_data_list_to_path(self.primary_data_path, self._data_primary)
    self._write_data_list_to_path(self.aux1_path, self._data_aux1)
    self._write_data_list_to_path(self.aux2_path, self._data_aux2)
    log.info('data primary size: {}, aux1 size: {}, aux2 size: {}'.format(len(self._data_primary), len(self._data_aux1), len(self._data_aux2)))

    self.aux1_dict = self._get_data_dict(self._data_aux1, key_col_name=self.aux1_key)
    self.aux2_dict = self._get_data_dict(self._data_aux2, key_col_name=self.aux2_key)

    # get truth data
    allcnt = 0
    aux1cnt = 0
    aux2cnt = 0
    for data in self._data_primary:
      allcnt += 1
      key = self._get_key_from_tfrecord(data, 'key')
      if key in self.aux1_dict:
        aux1cnt += 1
        data.MergeFrom(self.aux1_dict[key])
      if key in self.aux2_dict:
        aux2cnt += 1
        data.MergeFrom(self.aux2_dict[key])
      self.ans.append(data)
    log.info('local join data size:{}, aux1 join size:{} , aux2 join size{}'
            .format(allcnt, aux1cnt, aux2cnt))
