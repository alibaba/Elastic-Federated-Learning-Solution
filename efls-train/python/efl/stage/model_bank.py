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

import fnmatch
import six

from efl import exporter
from efl.framework import stage
from efl.utils import config

import tensorflow as tf

class ConfigItem(object):
  def __init__(self, ckpt_path, load_vars=None, exclude_vars=None):
    self._load_vars = load_vars if load_vars else []
    self._exclude_vars = exclude_vars if exclude_vars else []
    self._ckpt_path = ckpt_path
    self._vars_in_ckpt = {}
    self._var_list = {}
    self._ht_names = []
    self._init()

  def _init(self):
    self._get_ckpt_variables(self._ckpt_path)
    if len(self._load_vars) == 0 and len(self._exclude_vars) == 0:
      tf.logging.warning('model bank config is empty')
      return
  
    all_vars = set([])
    for var in tf.global_variables():
      all_vars.add(self._normalize_var_name(var.name))

    new_load_vars = {}
    if len(self._load_vars) > 0:
      if isinstance(self._load_vars, (list, tuple)):
        for var in self._load_vars:
          if isinstance(var, six.string_types):
            for var_in_ckpt in self._vars_in_ckpt:
              if fnmatch.fnmatch(var_in_ckpt, var) and var_in_ckpt in all_vars:
                new_load_vars[var_in_ckpt] = var_in_ckpt
          else:
            normalized_var_name = self._normalize_var_name(var.name)
            new_load_vars[normalized_var_name] = normalized_var_name
      elif isinstance(self._load_vars, dict):
        for key in self._load_vars:
          var_in_graph = self._item_to_string(self._load_vars[key])
          if var_in_graph in all_vars:
            new_load_vars[key] = var_in_graph
    self._load_vars = new_load_vars.copy()
    if len(self._exclude_vars) > 0:
      self._exclude_vars = [self._item_to_string(x) for x in self._exclude_vars]
      for var_in_ckpt in new_load_vars:
        for var in self._exclude_vars:
          if fnmatch.fnmatch(var_in_ckpt, var):
            del self._load_vars[var_in_ckpt]
    print("Model bank load variable dict: {}".format(self._load_vars))
    for name, item in self._load_vars.items():
      self._process_item(name, item)

  def _get_ckpt_variables(self, path):
    vars_in_ckpt = [x[0] for x in tf.train.list_variables(path)]
    for var in vars_in_ckpt:
      processed_name = self._process_var_name(var)
      if processed_name not in self._vars_in_ckpt:
        self._vars_in_ckpt[processed_name] = []
      self._vars_in_ckpt[processed_name].append(var)

  def _process_var_name(self, var_name):
    if var_name.endswith('/ids'):
      return var_name[:-4]
    if var_name.endswith('-keys'):
      return var_name[:-5]
    if var_name.endswith('-values'):
      return var_name[:-7]
    if var_name.endswith('-versions'):
      return var_name[:-9]
    for ht in self._ht_names:
      if var_name.startswith('{}/slots/'.format(ht)):
        return ht
    return var_name

  def _normalize_var_name(self, name):
    name_str = str(name)
    if name_str[-2:] == ':0':
      name_str = name_str[:-2]
    name_split = name_str.split("/")
    if len(name_split) > 1 and name_split[-1].startswith("part_"):
      name_str = name_str[:-len(name_split[-1])-1]
    return name_str

  def _item_to_string(self, item):
    if isinstance(item, six.string_types):
      return item
    else:
      return str(self._normalize_var_name(item.name))

  def _process_item(self, name, item):
    var = self._get_variable_by_name(item)
    if var is None:
      raise ValueError('no var:{} found in current model'.format(item))
    self._var_list[name] = var

  def _get_variable_by_name(self, name):
    if not isinstance(name, six.string_types):
      return name
    ori_name = name
    name = '{}:0'.format(name) if not name.endswith(':0') else name
    for v in tf.global_variables():
      if v.name == name:
        return v
    #deal with partitioned_variable
    parts = {}
    prefix = '{}/part_'.format(ori_name)
    for v in tf.global_variables():
      if v.name.startswith(prefix):
        try:
          parts[int(v.name[len(prefix):-2])] = v
        except:
          continue
    if len(parts) > 0:
      dim0 = 0
      for v in list(parts.values()):
        dim0 += v.shape[0]
      from tensorflow.python.ops import variables      
      return variables.PartitionedVariable(
        name=name,
        shape=[dim0] + parts[0].shape.as_list()[1:],
        dtype=parts[0].dtype,
        variable_list=list(parts.values()),
        partitions=[len(parts)] + [1]*(parts[0].shape.rank-1)) # fixme: support non dim0 partition 
    tf.logging.warning("can't find variable[{}] in current graph".format(name[0:-2]))
    return None

  def _get_slot_name(self, var):
    pos = var.find('/slots/')
    if pos == -1:
      return ''
    return var[pos+7:]

  @property
  def var_list(self):
    return self._var_list

  @property
  def ckpt_path(self):
    path = None
    try:
      path = tf.train.latest_checkpoint(self._ckpt_path)
    except:
      path = self._ckpt_path
    if path is None:
      path = self._ckpt_path
    return path

@exporter.export("stage.ModelBank")
class ModelBank(stage.Stage):
  def __init__(self, is_chief, config=None):
    super(ModelBank, self).__init__()
    self._is_chief = is_chief
    self._savers = {}
    self._config = self._init(config)

  def _init(self, config):
    if config is None:
      config = config.get_config('model_bank', default={})
    ret = {}
    for name, item in config.items():
      if name in ret:
        raise ValueError('duplicate model_bank:{}'.format(name))
      ret[name] = ConfigItem(item['path'], item['load'], item['exclude'])
      self._savers[name] = tf.train.Saver(var_list=ret[name]._var_list, sharded=True)
    return ret

  def run(self):
    if self._is_chief:
      for name, item in self._config.items():
        self._internal_run(name, item)

  def _internal_run(self, name, item):
    self._savers[name].restore(self.sess, item.ckpt_path)
