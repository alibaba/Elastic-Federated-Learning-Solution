# Copyright (C) 2016-2021 Alibaba Group Holding Limited
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

from tensorflow.keras.datasets import mnist
import os
import numpy as np
import tensorflow.compat.v1 as tf

def init_data():
  def build_tfrecord(file_path, sample_num, x, y, file_num=1):
    if not os.path.exists(file_path):
      os.mkdir(file_path)
    for j in range(file_num):
      writer = tf.python_io.TFRecordWriter(
          os.path.join(file_path, "data_{}.tfrd".format(j)))
      for i in range(sample_num):
        sample_id = np.array([j * sample_num + i])
        features = x[sample_id].flatten()
        label = np.array(y[sample_id])
        example = tf.train.Example(features=tf.train.Features(
            feature={
                'sample_id': tf.train.Feature(int64_list=tf.train.Int64List(value=sample_id)),
                'feature':tf.train.Feature(float_list=tf.train.FloatList(value=features)),
                'label':tf.train.Feature(float_list=tf.train.FloatList(value=label))
                }))
        writer.write(example.SerializeToString())
      writer.close()
  build_tfrecord("./leader_train", 6000, x_train_leader, y_train, file_num=10)
  build_tfrecord("./follower_train", 6000, x_train_follower, y_train, file_num=10)
  build_tfrecord("./leader_test", 1000, x_test_leader, y_test, file_num=10)
  build_tfrecord("./follower_test", 1000, x_test_follower, y_test, file_num=10)


if __name__ == '__main__':
  (x_train, y_train), (x_test, y_test) = mnist.load_data()
  x_train_leader, x_train_follower = x_train[:, :, :14], x_train[:, :, 14:]
  x_test_leader, x_test_follower = x_test[:, :, :14], x_test[:, :, 14:]
  init_data()
