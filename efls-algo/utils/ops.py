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


def build_mlp_layer(name, input, output_dim, activation_fn=tf.nn.leaky_relu, reuse=tf.AUTO_REUSE):
  fc = tf.layers.dense(input,
                       output_dim,
                       activation=activation_fn,
                       name=name,
                       kernel_initializer=tf.truncated_normal_initializer(stddev=0.001, dtype=tf.float32),
                       reuse=reuse)
  return fc

def poly(start, end, steps, total_steps, period, power):
    """
    Coe trick
    Default goes from start to end
    """
    total_steps = tf.cond(tf.less_equal(steps, total_steps),
                          lambda: total_steps,
                          lambda: steps)
    steps = tf.cast(steps, dtype=tf.float32) / 2
    total_steps = tf.cast(total_steps, dtype=tf.float32)
    delta = end - start
    base = total_steps * period[0]
    ceil = total_steps * period[1]
    return end - delta * (1. - (steps - base) / (ceil - base)) ** power

def mlp_gate(inputs, layer_dims, activation_fn=tf.nn.leaky_relu, scope="mlp_gate", reuse=tf.AUTO_REUSE):
  with tf.variable_scope(scope, reuse=reuse):
    input = tf.concat(inputs, axis=-1)
    for idx, dim in enumerate(layer_dims):
      if idx == len(layer_dims) - 1:
        act_fn = tf.nn.sigmoid
      else:
        act_fn = activation_fn
      input = build_mlp_layer("hiddenlayer_{}".format(idx), input, dim, activation_fn=act_fn, reuse=reuse)
    return input
