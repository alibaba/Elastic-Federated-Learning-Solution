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
from tensorflow.python.platform import tf_logging

def custom_scope_optimizer(scope_to_opt):
  def _custom_scope_optimizer(model, task):
    opt_to_vars = {}
    all_vars = tf.trainable_variables() + \
        tf.get_collection(ops.GraphKeys.TRAINABLE_RESOURCE_VARIABLES)
    scope_vars = []
    global_opt = scope_to_opt.pop('global', tf.train.GradientDescentOptimizer(0.001))
    for scope, opt in scope_to_opt.items():
      grad_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope=scope)
      if len(grad_vars) == 0:
        continue
      opt_to_vars[opt] = (grad_vars, scope)
      tf.logging.info(' --------- %s vars-------' % scope)
      tf.logging.info(grad_vars)
      scope_vars += grad_vars
    global_vars = []
    for var in all_vars:
      if var not in scope_vars:
        global_vars += [var]
    if len(global_vars) != 0:
      tf_logging.info('------------------- global vars -------------------')
      tf_logging.info(global_vars)
      opt_to_vars[global_opt] = (global_vars, None)
    return opt_to_vars
  return _custom_scope_optimizer
