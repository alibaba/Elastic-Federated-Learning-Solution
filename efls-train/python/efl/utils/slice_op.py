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

import tensorflow as tf

def slice_add(a, b):
  if isinstance(a, tf.Tensor) and isinstance(b, tf.Tensor):
    return tf.add(a, b)
  elif isinstance(a, tf.IndexedSlices) and isinstance(b, tf.IndexedSlices):
    equal_shape = tf.assert_equal(a.dense_shape, b.dense_shape)
    with tf.control_dependencies([equal_shape]):
      values = tf.concat([a.values, b.values], axis=0)
      indices = tf.concat([a.indices, b.indices], axis=0)
      uniq_indices, idx = tf.unique(indices)
      value_sum = tf.unsorted_segment_sum(values, idx, tf.shape(uniq_indices)[0])
      return tf.IndexedSlices(indices=uniq_indices,
                              values=value_sum,
                              dense_shape=a.dense_shape)
  else:
    raise ValueError("a and b should both be Tensor or IndexedSlices.")
