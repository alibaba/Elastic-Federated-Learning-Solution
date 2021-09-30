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

import argparse
import logging
import math
import os
import subprocess

from types import FunctionType
from multiprocessing import Pool, RLock

import numpy as np
import pandas as pd
import tensorflow as tf

parser = argparse.ArgumentParser(description="generate data arguments")
parser.add_argument('-d', '--data_path', required=True)
parser.add_argument('-o', '--output_dir', default="./data")
parser.add_argument('-t', '--train_data_ratio', type=float, default=0.9)
parser.add_argument('-p', '--parallel_num', type=int, default=10)
parser.add_argument('-b', '--block_rows', type=int, default=1000000)
parser.add_argument('-f', '--file_part_size', type=int, default=100000)
_CMD_ARGS, unknown = parser.parse_known_args()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

class ProcessPool(object):
  """
  multiprocessing pool helper class
  """

  DEFAULT_POOL = None

  def __init__(self, parallel_num):
    self._parallel_num = parallel_num

  @classmethod
  def get_default_pool(cls):
    if cls.DEFAULT_POOL is None:
      cls.DEFAULT_POOL = ProcessPool(_CMD_ARGS.parallel_num)
    return cls.DEFAULT_POOL

  def apply_async(self, func, args, callback, parallel_num=None):
    if isinstance(func, FunctionType):
      task_name = func.__name__
    else:
      task_name = func.__class__.__name__
    logging.info('{} begin, args: {} ...'.format(task_name, args))

    if not parallel_num:
      parallel_num = self._parallel_num
    err_cb = lambda x : logging.error(x)
    try:
      pool = Pool(parallel_num)
      tasks = [pool.apply_async(func, arg, callback=callback, error_callback=err_cb) for arg in args]
      for task in tasks:
        task.wait()
      # check status
      all_success = all([task.successful() for task in tasks])
      # TODO: remove this from ProcessPool
      if not all_success:
        logging.error("{} running failed, exit ...".format(task_name))
        exit(1)
      logging.info('{} end ...'.format(task_name))
    finally:
      pool.close()
      pool.join()


class SyncBaseTask(object):
  """
  Task base class
  """

  def __init__(self, sample_cnt, block_rows):
    self._sample_cnt = sample_cnt
    self._block_rows = block_rows

  def generate_args(self):
    return [[i] for i in range(int(math.ceil(self._sample_cnt / self._block_rows)))]

  def callback(self, *args, **kwargs):
    glock.acquire()
    try:
      self._cb(*args, **kwargs)
    finally:
      glock.release()

  def _cb(self, *args, **kwargs):
    raise NotImplementedError("_cb must be implemented")

  @classmethod
  def reset_cls_cache(cls):
    raise NotImplementedError("reset_cls_cache must be implemented")


class DropColumnsTask(SyncBaseTask):
  """
  Drop columns task class
  """
  _data = []

  def __init__(self, data_path, sample_cnt, block_rows):
    super(DropColumnsTask, self).__init__(sample_cnt, block_rows)
    self._data_path = data_path

  @property
  def data(self):
    return self._data

  def _cb(self, *args, **kwargs):
    self._data.append(args[0])

  def __call__(self, idx):
    return pd.read_table(self._data_path,
                         header=None,
                         skiprows=self._block_rows * idx,
                         nrows=self._block_rows) \
           .drop(axis=1, columns=[1, 10, 12, 32, 33, 35, 38, 39]) \
           .dropna()

  @classmethod
  def reset_cls_cache(cls):
    cls._data = []


class ComputeSumTask(SyncBaseTask):
  """
  Compute sum task class
  """
  _columns_sum = 0
  _dense_features = None

  def __init__(self, sample_cnt, block_rows):
    super(ComputeSumTask, self).__init__(sample_cnt, block_rows)

  @property
  def columns_sum(self):
    return self._columns_sum

  def _cb(self, *args, **kwargs):
    self._columns_sum = args[0] + self._columns_sum

  def __call__(self, idx):
    start = idx * self._block_rows
    end = (idx+1) * self._block_rows
    return self._dense_features[start:end].sum(axis=0)

  @classmethod
  def reset_cls_cache(cls):
    cls._columns_sum = 0
    cls._dense_features = None


class ComputeErrorSquareSumTask(SyncBaseTask):
  """
  Compute error square sum task class
  """
  _columns_error_square_sum = 0
  _dense_features = None
  _columns_mean = None

  def __init__(self, sample_cnt, block_rows):
    super(ComputeErrorSquareSumTask, self).__init__(sample_cnt, block_rows)

  @property
  def columns_error_square_sum(self):
    return self._columns_error_square_sum

  def _cb(self, *args, **kwargs):
    self._columns_error_square_sum = args[0] + self._columns_error_square_sum

  def __call__(self, idx):
    start = idx * self._block_rows
    end = (idx + 1) * self._block_rows
    return ((self._dense_features[start:end] - self._columns_mean) ** 2).sum(axis=0)

  @classmethod
  def reset_cls_cache(cls):
    cls._columns_error_square_sum = 0
    cls._dense_features = None
    cls._columns_mean = None


class ComputeZScoreTask(SyncBaseTask):
  """
  Compute z score task class
  """
  _data = []
  _dense_features = None
  _columns_mean = None
  _columns_std = None

  def __init__(self, sample_cnt, block_rows):
    super(ComputeZScoreTask, self).__init__(sample_cnt, block_rows)

  @property
  def data(self):
    return self._data

  def _cb(self, *args, **kwargs):
    self._data.append(args[0])

  def __call__(self, idx):
    start = idx * self._block_rows
    end = (idx + 1) * self._block_rows
    return (self._dense_features[start:end] - self._columns_mean) / self._columns_std

  @classmethod
  def reset_cls_cache(cls):
    cls._data = []
    cls._dense_features = None
    cls._columns_mean = None
    cls._columns_std = None


class BuildTfRecordTask(object):
  """
  Build tfrd task class
  """
  def __init__(self, kwargs):
    self._kwargs = kwargs

  def generate_args(self):
    args = []
    for data_name, (part_size, output_dir) in self._kwargs.items():
      label, _, _ = self.get_feature_group_by_name(data_name)
      for i in range(math.ceil(label.shape[0] / float(part_size))):
        end = min(label.shape[0], (i + 1) * part_size)
        args += [[data_name, i * part_size, end, i, output_dir]]
    return args

  def callback(self, *args, **kwargs):
    pass

  def build_leader_tfrecord(self, file_path, start, end, categorical, label, file_num):
    glock.acquire()
    try:
      if not os.path.exists(file_path):
        os.makedirs(file_path)
    finally:
      glock.release()
    writer = tf.io.TFRecordWriter(
        os.path.join(file_path, "data_{}.tfrd".format(file_num)))
    positive_cnt = 0
    negative_cnt = 0
    for i in range(start, end):
      sample_id = np.array([i])
      categorical_ = categorical[sample_id]
      label_ = label[sample_id].flatten()
      positive_cnt += label_[label_ > 0].size
      negative_cnt += label_[label_ < 1].size
      feature = {'feature' + str(k): tf.train.Feature(bytes_list=tf.train.BytesList(value=categorical_[:, k]))
          for k in range(categorical.shape[1])}
      feature.update({'sample_id': tf.train.Feature(int64_list=tf.train.Int64List(value=sample_id))})
      feature.update({'label':tf.train.Feature(int64_list=tf.train.Int64List(value=label_))})
      example = tf.train.Example(features=tf.train.Features(
          feature=feature))
      writer.write(example.SerializeToString())
    writer.close()
    logging.info('build leader tfrecord success: file_path [%s] count [%d] positive_cnt [%d] negative_cnt [%d] file_num [%d]' % (file_path, end-start, positive_cnt, negative_cnt, file_num))

  def build_follower_tfrecord(self, file_path, start, end, dense, file_num):
    if not os.path.exists(file_path):
      os.makedirs(file_path)
    writer = tf.io.TFRecordWriter(
        os.path.join(file_path, "data_{}.tfrd".format(file_num)))
    for i in range(start, end):
      sample_id = np.array([i])
      dense_ = dense[sample_id].flatten()
      example = tf.train.Example(features=tf.train.Features(
          feature={
              'sample_id': tf.train.Feature(int64_list=tf.train.Int64List(value=sample_id)),
              'dense':tf.train.Feature(float_list=tf.train.FloatList(value=dense_))
              }))
      writer.write(example.SerializeToString())
    writer.close()
    logging.info('build follower tfrecord success: file_path [%s] count [%d] file_num [%d]' % (file_path, end-start, file_num))

  def get_feature_group_by_name(self, name):
    if name == "train":
      label = self._labels_train
      categorical = self._categorical_features_train
      dense = self._dense_features_train
    elif name == "test":
      label = self._labels_test
      categorical = self._categorical_features_test
      dense = self._dense_features_test
    else:
      raise ValueError("not supported")
    return label, categorical, dense
  
  def __call__(self, name, start, end, file_no, output_dir):
    label, categorical, dense = self.get_feature_group_by_name(name)
    assert label.shape[0] == categorical.shape[0] == dense.shape[0]
    self.build_leader_tfrecord(output_dir % "leader", start, end, categorical, label, file_no)
    self.build_follower_tfrecord(output_dir % "follower", start, end, dense, file_no)


def dense_preprocess(dense_features, sample_cnt, block_rows):
  ComputeSumTask._dense_features = dense_features
  cst = ComputeSumTask(sample_cnt, block_rows)
  pool.apply_async(cst, cst.generate_args(), cst.callback)
  columns_mean = cst.columns_sum / sample_cnt

  ComputeErrorSquareSumTask._dense_features = dense_features
  ComputeErrorSquareSumTask._columns_mean = columns_mean
  cesst = ComputeErrorSquareSumTask(sample_cnt, block_rows)
  pool.apply_async(cesst, cesst.generate_args(), cesst.callback)
  columns_std = (cesst.columns_error_square_sum / sample_cnt).apply(np.sqrt)

  ComputeZScoreTask._dense_features = dense_features
  ComputeZScoreTask._columns_mean = columns_mean
  ComputeZScoreTask._columns_std = columns_std
  czst = ComputeZScoreTask(sample_cnt, block_rows)
  pool.apply_async(czst, czst.generate_args(), czst.callback)

  return czst.data

def data_preprocess(data_path, train_data_ratio, block_rows):
  def _data_count():
    return int(subprocess.getoutput("wc -l {}".format(data_path)).split()[0])

  sample_cnt = _data_count()
  # clean data
  dct = DropColumnsTask(data_path, sample_cnt, block_rows)
  pool.apply_async(dct, dct.generate_args(), dct.callback)

  negative_cnt = positive_cnt = sample_cnt // 2
  data = pd.concat(dct.data).sample(frac=1)
  data = pd.concat([data.loc[data[0] < 1][:negative_cnt], data.loc[data[0] > 0][:positive_cnt]]).sample(frac=1)

  #clear cache
  DropColumnsTask.reset_cls_cache()
 
  train_data_num = int(train_data_ratio * data.shape[0])
  negative_cnt = data.loc[data[0] < 1].shape[0]
  positive_cnt = data.loc[data[0] > 0].shape[0]
  logging.info('total data num: [%s] positive_cnt: [%s] negative_cnt: [%s]' % (data.shape[0], positive_cnt, negative_cnt))
  train_data, test_data = data[:train_data_num], data[train_data_num:]
  return train_data, test_data

def column_sample(data, block_rows):
  sample_cnt = data.shape[0]

  labels = data.pop(0).values
  categorical_features = data.iloc[:, 10:].applymap(lambda a: bytes(a, 'utf8')).values
  dense_features = dense_preprocess(data.iloc[:, :10], sample_cnt, block_rows)
  dense_features = pd.concat(dense_features).values

  # clear cache
  ComputeSumTask.reset_cls_cache()
  ComputeErrorSquareSumTask.reset_cls_cache()
  ComputeZScoreTask.reset_cls_cache()

  return labels, categorical_features, dense_features

if __name__ == '__main__':
  glock = RLock()
  pool = ProcessPool.get_default_pool()
  block_rows = _CMD_ARGS.block_rows

  assert _CMD_ARGS.train_data_ratio >= 0. and _CMD_ARGS.train_data_ratio <= 1.
  train_data, test_data = data_preprocess(_CMD_ARGS.data_path, _CMD_ARGS.train_data_ratio, block_rows)
  labels_train, categorical_features_train, dense_features_train = column_sample(train_data, block_rows)
  del train_data
  labels_test, categorical_features_test, dense_features_test = column_sample(test_data, block_rows)
  del test_data

  BuildTfRecordTask._labels_train = labels_train
  BuildTfRecordTask._categorical_features_train = categorical_features_train
  BuildTfRecordTask._dense_features_train = dense_features_train
  BuildTfRecordTask._labels_test = labels_test
  BuildTfRecordTask._categorical_features_test = categorical_features_test
  BuildTfRecordTask._dense_features_test = dense_features_test

  params = {
    'train': [_CMD_ARGS.file_part_size, _CMD_ARGS.output_dir + '/%s/train'],
    'test': [_CMD_ARGS.file_part_size, _CMD_ARGS.output_dir + '/%s/test']
  }
  btrd = BuildTfRecordTask(params)
  pool.apply_async(btrd, btrd.generate_args(), btrd.callback)
