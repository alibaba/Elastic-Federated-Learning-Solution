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

import tensorflow_io
from tensorflow.python.platform import gfile
from xfl.data.local_join import utils
import tensorflow as tf
from xfl.common.logger import log
class AuxTable(object):
  def __init__(self,
               path: str,
               key_col: str):
    self.path = path
    self.key_col = key_col
    self.store = {}
    self._inited = False
  def open(self):
    if not self._inited:
      utils.assert_valid_dir(path=self.path)
      files = utils.list_data_file_recursively(self.path)
      for f in files:
        if not gfile.Exists(f):
          raise RuntimeError("path {} does not exist. please check your config!".format(f))
        dataset = tf.data.TFRecordDataset(f)
        for raw_record in dataset:
          example = tf.train.Example()
          example.ParseFromString(raw_record.numpy())
          if self.key_col not in example.features.feature:
            raise RuntimeError("key col {} is not in input record, please check your data.".format(self.key_col))
          if not example.features.feature[self.key_col].WhichOneof('kind') == 'bytes_list':
            raise RuntimeError(
              "key col {} type must be bytes_list, but got {}".format(self.key_col, example.features.feature[self.key_col].WhichOneof('kind')))
          if not len(example.features.feature[self.key_col].bytes_list.value) == 1:
            raise RuntimeError(
              "key col {} length must be 1, but got {}".format(self.key_col, len(example.features.feature[self.key_col].bytes_list.value)))
          self.store[example.features.feature[self.key_col].bytes_list.value[0]] = raw_record.numpy()
      log.info("Aux table {} load successfully, size:{}".format(self.path, len(self.store)))
      self._inited = True
    else:
      log.info("Aux table {} has been inited. skip it!".format(self.path))


  def get(self, key):
    return self.store.get(key, None)

  def get_batch(self, keys: list):
    return [self.store.get(i) for i in keys]
