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

import math
import sys

import tensorflow as tf
from efl.lib import ops as fed_ops
import numpy as np

class FixedPointTensor():

  BASE = 16.
  LOG2_BASE = math.log(BASE, 2)
  FLOAT_MANTISSA_BITS = sys.float_info.mant_dig
  Q = 293973345475167247070445277780365744413
  TF_CONVERT_NUM_LENGTH = 31

  def __init__(self, n=None, max_int=None):
    if n is None:
      n = Q
      max_int = Q // 3 - 1
    self._n = n
    self._max_int = max_int
    self._encoding = None
    self._exponent = None

  @property
  def encoding(self):
    return self._encoding

  @property
  def exponent(self):
    return self._exponent

  def set_encoding(self, encoding, exponent):
    self._encoding = encoding
    self._exponent = exponent
    return self

  def encode(self, scalar, max_exponent=None):
    scalar = tf.where(tf.less_equal(tf.math.abs(scalar), 1e-200),
                      tf.zeros_like(scalar),
                      scalar)
    if scalar.dtype in (tf.int8, tf.int16, tf.int32, tf.int64):
      exponent = tf.zeros_like(scalar, dtype=tf.float32)
    elif scalar.dtype in (tf.float16, tf.float32, tf.float64):
      scalar = tf.cast(scalar, tf.float32)
      _, flt_exponent = fed_ops.frexp(scalar)
      lsb_exponent = FixedPointTensor.FLOAT_MANTISSA_BITS - flt_exponent
      exponent = tf.math.floor(lsb_exponent / FixedPointTensor.LOG2_BASE)
    else:
      raise ValueError(f"FixedPointTensor not support encode for type: {scalar.dtype}")
    if max_exponent is not None:
      max_exponent = tf.ones_like(scalar, dtype=tf.float32) * max_exponent
      max_exponent = tf.where(tf.greater(max_exponent, exponent), max_exponent, exponent)
      diff_exponent = tf.cast(max_exponent - exponent, dtype=tf.int64)
    else:
      diff_exponent = tf.zeros_like(scalar, dtype=tf.int64)
      max_exponent = exponent

    n = tf.constant(str(self._n), dtype=tf.string, shape=[1] * len(scalar.get_shape()))
    n = tf.tile(n, tf.shape(scalar))
    int_fixpoint = tf.round(scalar * tf.pow(tf.cast(FixedPointTensor.BASE, tf.float32), exponent))
    fixpoint = tf.strings.as_string(tf.cast(int_fixpoint, dtype=tf.int64))
    base = tf.constant(str(int(FixedPointTensor.BASE)), dtype=tf.string, shape=[1] * len(scalar.get_shape()))
    base = tf.tile(base, tf.shape(scalar))
    pow_base = fed_ops.gmp_pow(base, diff_exponent)
    fixpoint = fed_ops.gmp_mul(fixpoint, pow_base)
    encoding = fed_ops.gmp_mod(fixpoint, n)
    self._encoding = encoding
    self._exponent = max_exponent
    return self

  def _format_encode(self, encoded, exponent):
    expand_exponent = tf.zeros_like(exponent, dtype=tf.float32)
    expand_length = tf.cast(tf.strings.length(encoded) - FixedPointTensor.TF_CONVERT_NUM_LENGTH, dtype=tf.float32)
    expand_exponent = tf.where(tf.greater(expand_length, 0), expand_length, expand_exponent)
    base = tf.constant(str(int(FixedPointTensor.BASE)), dtype=tf.string, shape=[1] * len(encoded.get_shape()))
    base = tf.tile(base, tf.shape(encoded))
    pow_base = fed_ops.gmp_pow(base, tf.cast(expand_exponent, dtype=tf.int64))
    self._encoding = fed_ops.gmp_div(encoded, pow_base)
    self._exponent = exponent - expand_exponent

  def decode(self):
    max_int = tf.constant(str(self._max_int), dtype=tf.string, shape=[1] * len(self._encoding.get_shape()))
    max_int = tf.tile(max_int, tf.shape(self._encoding))
    n = tf.constant(str(self._n), dtype=tf.string, shape=[1] * len(self._encoding.get_shape()))
    n = tf.tile(n, tf.shape(self._encoding))
    cmp_result = fed_ops.gmp_cmp(self._encoding, max_int)
    pos_matrix = tf.less_equal(cmp_result, 0)
    encoded = tf.where(pos_matrix, self.encoding, fed_ops.gmp_sub(n, self.encoding))
    self._format_encode(encoded, self.exponent)
    encoded = tf.strings.to_number(self.encoding, tf.float32)
    pos_matrix = tf.cast(pos_matrix, tf.float32) * 2. - 1.
    decoded = encoded * tf.pow(tf.cast(FixedPointTensor.BASE, tf.float32), -self.exponent)
    return decoded * pos_matrix
