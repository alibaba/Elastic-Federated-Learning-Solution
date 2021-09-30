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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

import tensorflow as tf
from tensorflow.python.platform import gfile
from tensorflow.python.data.ops import dataset_ops
from tensorflow.python.ops import control_flow_ops
from tensorflow.python.ops import gen_control_flow_ops
from tensorflow.python.framework import ops
from tensorflow.python.data.experimental.ops import interleave_ops
from tensorflow.python.ops import gen_math_ops

from efl.dataio.work_queue import WorkQueue, FederalWorkQueue
from efl.dataio.federal_dataset import FederalDataset
from efl.dataio.dataio_hook import DataIOHook, FederalDataIOHook
from efl.lib import ops as fed_ops
from efl import exporter

_DATAIO_END_FILE_ = "__DATA_IO_END_FILE_NAME__"

@exporter.export("data.DataIO")
class DataIO(object):

  def __init__(self,
               data_base_dir,
               batch_size,
               worker_idx,
               worker_num,
               prefetch=1,
               num_epochs=1,
               save_interval=100,
               drop_remainder=False,
               name='dataio'):
    self._data_base_dir = data_base_dir
    self._file_nodes = []
    self._feature_map = {}
    self._batch_size = batch_size
    self._worker_idx = worker_idx
    self._worker_num = worker_num
    self._save_interval = save_interval
    self._num_epochs = num_epochs
    self._prefetch = prefetch
    self._name = name
    self._drop_remainder = drop_remainder
    self._initialize = False

  def add_file_node(self, file_node):
    if self._initialize:
      raise RuntimeError('DataIO has finalized, you cannot add file after read.')
    self._file_nodes.append(file_node)

  def add_file_nodes(self, file_nodes):
    for file_node in file_nodes:
      self.add_file_node(file_node)

  def _list_block_ids(self):
    if not self._file_nodes:
      file_list = self._listdir_recursive(self._data_base_dir)
    else:
      file_list = []
      for file_node in self._file_nodes:
        file_node = os.path.join(self._data_base_dir, file_node)
        file_list.extend(self._listdir_recursive(file_node))
    file_list.sort()
    return file_list

  def _listdir_recursive(self, file_path):
    file_list = []
    for base_dir, _, filenames in gfile.Walk(file_path):
      file_list.extend([os.path.join(base_dir, f) for f in filenames])
    return file_list

  def _get_full_file_name(self, block_id):
    return block_id

  def fixedlen_feature(self, name, dim, dtype=tf.float32):
    if self._initialize:
      raise RuntimeError('DataIO has finalized, you cannot add fixlen feature after read.')
    if name in self._feature_map:
      raise ValueError("Feature name already exist, please check, feature name: {}".format(name))
    self._feature_map[name] = tf.io.FixedLenFeature([dim], dtype)

  def varlen_feature(self, name, dtype=tf.int64):
    if self._initialize:
      raise RuntimeError('DataIO has finalized, you cannot add varlen feature after read.')
    if name in self._feature_map:
      raise ValueError("Feature name already exist, please check, feature name: {}".format(name))
    self._feature_map[name] = tf.io.VarLenFeature(dtype)

  def _parse_function(self, example_proto):
    parse_feature = tf.io.parse_example(example_proto, self._feature_map)
    return parse_feature

  def restore_from_reader_state_op(self, reader_state):
    return fed_ops.deserialize_iterator_from_string(
        self._iterator._iterator_resource, reader_state)

  def read(self):
    if not self._initialize:
      self._initialize_internal()
      self._iterator = dataset_ops.make_initializable_iterator(self._dataset)
      self._batch = self._iterator.get_next()
      self._batch = self._parse_function(self._batch)
      self._initialize = True
    return self._batch

  def init_dataset(self):
    work_queue = WorkQueue(self._list_block_ids(),
                           num_epochs=self._num_epochs,
                           shuffle=False,
                           name=self._name + "_queue")
    dataset = work_queue.input_dataset()

    def generate_dataset_fn(filename):
      fullname = self._get_full_file_name(filename)
      return FederalDataset(fullname, filename)

    dataset = dataset.interleave(
        generate_dataset_fn, 1)
    return dataset

  def initialize_iter(self, sess):
    if not self._initialize:
      raise RuntimeError('DataIO has not finalized, you should call this function after read.')
    sess.run(self._iterator.initializer)

  def _initialize_internal(self):
    dataset = self.init_dataset()
    dataset = dataset.batch(self._batch_size, drop_remainder=self._drop_remainder)
    if self._prefetch:
      dataset.prefetch(self._prefetch)
    self._dataset = dataset

  def get_hook(self):
    return DataIOHook(self,
                      task_index=self._worker_idx,
                      task_num=self._worker_num,
                      save_interval=self._save_interval,
                      name=self._name)


@exporter.export("data.FederalDataIO")
class FederalDataIO(DataIO):

  def __init__(self,
               data_base_dir,
               batch_size,
               communicator,
               role,
               worker_idx,
               worker_num,
               prefetch=1,
               num_epochs=1,
               save_interval=100,
               data_mode='data-join',
               name='dataio'):
    super(FederalDataIO, self).__init__(data_base_dir=data_base_dir,
                                        batch_size=batch_size,
                                        worker_idx=worker_idx,
                                        worker_num=worker_num,
                                        prefetch=prefetch,
                                        num_epochs=num_epochs,
                                        save_interval=save_interval,
                                        name=name)
    if role not in ('leader', 'follower'):
      raise ValueError("role must be one of `leader` or `follower`")
    if data_mode not in ('local', 'data-join'):
      raise ValueError("data_mode must be one of `local` or `data-join`")
    self._communicator = communicator
    self._role = role
    self._data_mode = data_mode
    self._random_id_cache = {}

  def init_dataset(self):
    def generate_dataset_leader_map_fn(filename):
      if self._data_mode == "data-join":
        filename = tf.strings.regex_replace(filename, 'part(-.*)-', 'part-*-')
      cond_op = tf.cond(gen_math_ops.equal(filename, _DATAIO_END_FILE_),
          lambda: self._communicator.terminate_reader(self._name),
          lambda: self._communicator.send_reader_state(self._name, filename, 0))
      with ops.control_dependencies([cond_op]):
        fullname = self._get_full_file_name(filename)
        return fullname, filename

    def generate_dataset_leader_flatmap_fn(fullname, filename):
      return FederalDataset(fullname, filename)

    def generate_dataset_follower_map_fn(_):
      filename, sample_index = self._communicator.recv_reader_state(self._name)
      fullname = self._get_full_file_name(filename)
      return fullname, filename, sample_index

    def generate_dataset_follower_flatmap_fn(fullname, filename, sample_index):
      return FederalDataset(fullname, filename, sample_index=sample_index)

    if self._role == 'leader':
      block_ids = self._list_block_ids()
      work_queue = FederalWorkQueue(block_ids,
                                    self._num_epochs,
                                    shuffle=False,
                                    name=self._name)
      dataset = work_queue.input_dataset()
      dataset = dataset.map(generate_dataset_leader_map_fn)
      dataset = dataset.interleave(
          generate_dataset_leader_flatmap_fn, 1)
      return dataset
    else:
      dataset = dataset_ops.Dataset.from_tensors(0).repeat()
      dataset = dataset.map(generate_dataset_follower_map_fn)
      dataset = dataset.interleave(
          generate_dataset_follower_flatmap_fn, 1)
      return dataset

  def _list_block_ids(self):
    if not self._file_nodes:
      file_list = self._listdir_recursive(self._data_base_dir)
    else:
      file_list = []
      for file_node in self._file_nodes:
        file_node = os.path.join(self._data_base_dir, file_node)
        file_list.extend(self._listdir_recursive(file_node))
    # keep file name out of base dir
    file_list = [f[len(self._data_base_dir) + 1:] for f in file_list]
    file_list.sort()
    return file_list

  def _get_random_id(self, file_name):
    def get_id(f):
      file_path = os.path.split(f)[0]
      if not file_path in self._random_id_cache:
        files = gfile.ListDirectory(file_path)
        random_id = files[0].split('part-')[1]
        random_id = "part-" + random_id[:-len(random_id.split('-')[-1])]
        self._random_id_cache[file_path] = random_id
      return self._random_id_cache[file_path]
    random_id = tf.py_func(func=get_id, inp=[file_name], Tout=tf.string, stateful=False)
    return random_id

  def _get_full_file_name(self, block_id):
    file_name = tf.strings.join([self._data_base_dir, block_id], separator='/')
    if self._data_mode == "data-join":
      data_join_random_id = self._get_random_id(file_name)
      file_name = tf.strings.regex_replace(file_name, 'part-\*-', data_join_random_id)
    return file_name

  def get_hook(self):
    return FederalDataIOHook(self,
                            self._communicator,
                            self._role,
                            task_index=self._worker_idx,
                            task_num=self._worker_num,
                            save_interval=self._save_interval,
                            name=self._name)
