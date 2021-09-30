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

import os
import math
from multiprocessing import Pool, RLock
import numpy as np
import pandas as pd
import tensorflow as tf

def drop_columns(idx, block_rows):
  return pd.read_table('train.txt',
                       header=None,
                       skiprows=block_rows * idx,
                       nrows=block_rows)\
      .drop(axis=1, columns=[1, 10, 12, 32, 33, 35, 38, 39])\
      .dropna()

def compute_sum(dense_features, start, end):
  block = dense_features[start:end].sum(axis=0)
  return block

def compute_error_square_sum(dense_features, start, end, columns_mean):
  return ((dense_features[start:end] - columns_mean) ** 2).sum(axis=0)

def compute_z_score(dense_features, start, end, columns_mean, columns_std):
  return (dense_features[start:end] - columns_mean) / columns_std

def build_follower_tfrecord(file_path, start, end, categorical, file_num):
  if not os.path.exists(file_path):
    os.mkdir(file_path)
  writer = tf.io.TFRecordWriter(
      os.path.join(file_path, "data_{}.tfrd".format(file_num)))
  for i in range(start, end):
    sample_id = np.array([i])
    categorical_ = categorical[sample_id]
    feature = {'feature' + str(k): tf.train.Feature(bytes_list=tf.train.BytesList(value=categorical_[:, k]))
        for k in range(21)}
    feature.update({'sample_id': tf.train.Feature(int64_list=tf.train.Int64List(value=sample_id))})
    example = tf.train.Example(features=tf.train.Features(
        feature=feature))
    writer.write(example.SerializeToString())
  writer.close()

def build_leader_tfrecord(file_path, start, end, dense, label, file_num):
  if not os.path.exists(file_path):
    os.mkdir(file_path)
  writer = tf.io.TFRecordWriter(
      os.path.join(file_path, "data_{}.tfrd".format(file_num)))
  for i in range(start, end):
    sample_id = np.array([i])
    dense_ = dense[sample_id].flatten()
    label_ = label[sample_id].flatten()
    example = tf.train.Example(features=tf.train.Features(
        feature={
            'sample_id': tf.train.Feature(int64_list=tf.train.Int64List(value=sample_id)),
            'dense':tf.train.Feature(float_list=tf.train.FloatList(value=dense_)),
            'label':tf.train.Feature(int64_list=tf.train.Int64List(value=label_))
            }))
    writer.write(example.SerializeToString())
  writer.close()

if __name__ == '__main__':
  lock = RLock()
  pool = Pool(os.cpu_count() - 1)

  data = []
  def add_block(block):
    lock.acquire()
    try:
      data.append(block)
    finally:
      lock.release()

  sample_cnt = 45840617
  block_rows = 1000000
  tasks = [pool.apply_async(drop_columns,
                            (i, block_rows),
                            callback=add_block)
           for i in range(int(math.ceil(sample_cnt / block_rows)))]
  for task in tasks:
    task.wait()

  sample_cnt = 11800000
  negative_cnt = positive_cnt = sample_cnt // 2
  data = pd.concat(data)
  data = data.sample(frac=1)
  data = pd.concat([data.loc[data[0] < 1][:negative_cnt], data.loc[data[0] > 0][:positive_cnt]]).sample(frac=1)
  labels = data.pop(0)
  dense_features = data.iloc[:, :10]
  categorical_features = data.iloc[:, 10:]

  columns_sum = 0
  def add_block_sum(block_sum):
    lock.acquire()
    try:
      global columns_sum
      columns_sum = block_sum + columns_sum
    finally:
      lock.release()

  tasks = [pool.apply_async(compute_sum,
                            (dense_features, i * block_rows, (i + 1) * block_rows),
                            callback=add_block_sum)
           for i in range(int(math.ceil(sample_cnt / block_rows)))]
  for task in tasks:
    task.wait()
  columns_mean = columns_sum / sample_cnt

  columns_error_square_sum = 0
  def add_block_error_square_sum(block_error_square_sum):
    lock.acquire()
    try:
      global columns_error_square_sum
      columns_error_square_sum = block_error_square_sum + columns_error_square_sum
    finally:
      lock.release()

  tasks = [pool.apply_async(compute_error_square_sum,
                            (dense_features, i * block_rows, (i + 1) * block_rows, columns_mean),
                            callback=add_block_error_square_sum)
           for i in range(int(math.ceil(sample_cnt / block_rows)))]
  for task in tasks:
    task.wait()

  columns_std = (columns_error_square_sum / sample_cnt).apply(np.sqrt)
  data = []
  tasks = [pool.apply_async(compute_z_score,
                            (dense_features, i * block_rows, (i + 1) * block_rows, columns_mean, columns_std),
                            callback=add_block)
           for i in range(int(math.ceil(sample_cnt / block_rows)))]
  for task in tasks:
    task.wait()
  dense_features = pd.concat(data)

  dense_features = dense_features.values
  labels = labels.values
  categorical_features = categorical_features.applymap(lambda a: bytes(a, 'utf8')).values

  dense_features_train = dense_features[:8000000]
  labels_train = labels[:8000000]
  categorical_features_train = categorical_features[:8000000]
  dense_features_test = dense_features[8000000:]
  labels_test = labels[8000000:]
  categorical_features_test = categorical_features[8000000:]

  for i in range(80):
    build_leader_tfrecord('leader_train', i * 100000, (i + 1) * 100000, dense_features_train, labels_train, i)
    build_follower_tfrecord('follower_train', i * 100000, (i + 1) * 100000, categorical_features_train, i)
  for i in range(38):
    build_leader_tfrecord('leader_test', i * 100000, (i + 1) * 100000, dense_features_test, labels_test, i)
    build_follower_tfrecord('follower_test', i * 100000, (i + 1) * 100000, categorical_features_test, i)

  pool.close()
  pool.join()

