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

import tensorflow.compat.v1 as tf
from tensorflow.python.framework import ops

from efl import exporter
from efl.utils import config

r'''builtin optimizer fn'''
@exporter.export('optimizer_fn.optimizer_setter')
def optimzier_setter(opt):
  def _optimizer_setter(model, task):
    opt_to_vars = {}
    grad_vars = tf.trainable_variables() + \
        ops.get_collection(ops.GraphKeys.TRAINABLE_RESOURCE_VARIABLES)
    opt_to_vars[opt] = (grad_vars, None)
    return opt_to_vars
  return _optimizer_setter

@exporter.export('optimizer_fn.scope_optimizer')
def scope_optimizer(scope_to_opt):
  def _scope_optimizer(model, task):
    opt_to_vars = {}
    for scope, opt in scope_to_opt.items():
      grad_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope=scope)
      opt_to_vars[opt] = (grad_vars, scope)
    return opt_to_vars
  return _scope_optimizer

_OPT_DICT = {}
_OPT_DICT['sgd'] = tf.train.GradientDescentOptimizer
_OPT_DICT['momentum'] = tf.train.MomentumOptimizer
_OPT_DICT['adagrad'] = tf.train.AdagradOptimizer
_OPT_DICT['adam'] = tf.train.AdamOptimizer

@exporter.export('optimizer_fn.config_optimizer')
def config_optimizer(model, task):
  def _create_optimizer_from_conf():
    name = config.get_config("optimizer", "name")
    params = config.get_config("optimizer", "params")
    if name is None or params is None:
      raise ValueError("miss name or params in config")
    return _OPT_DICT[name](**params)
  opt_to_vars = {}
  opt = _create_optimizer_from_conf()
  grad_vars = tf.trainable_variables() + \
      ops.get_collection(ops.GraphKeys.TRAINABLE_RESOURCE_VARIABLES)
  opt_to_vars[opt] = (grad_vars, None)
  return opt_to_vars
