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
import numpy as np

from efl.privacy.fixedpoint_tensor import FixedPointTensor
from efl.lib import ops as fed_ops

class PaillierTensor(object):

  def __init__(self, public_key):
    self._public_key = public_key

  def _raw_encrypt(self, plaintext):
    public_n = self._strings_like(self.public_key.n, plaintext)
    public_nsquare = self._strings_like(self.public_key.nsquare, plaintext)
    ones_string = self._strings_like(1, plaintext)
    pos_matrix = self._pos_matrix(plaintext)
    plaintext = tf.where(pos_matrix, plaintext,
                         fed_ops.gmp_sub(public_n, plaintext))
    ciphertext = fed_ops.gmp_mul(public_n, plaintext)
    ciphertext = fed_ops.gmp_add(ciphertext, ones_string)
    ciphertext = fed_ops.gmp_mod(ciphertext, public_nsquare)
    ciphertext = tf.where(pos_matrix, ciphertext,
                          fed_ops.gmp_invert(ciphertext, public_nsquare))
    return ciphertext

  def encrypt(self, inputs):
    fp = FixedPointTensor(self.public_key.n, self.public_key.max_int)
    fp = fp.encode(inputs, None)
    cipher = self._raw_encrypt(fp.encoding)
    exponent = fp.exponent
    self._ciphertext = cipher
    self._exponent = exponent
    return self

  def set_ciphertext(self, ciphertext, exponent=None):
    self._ciphertext = ciphertext
    if exponent is None:
      exponent = tf.zeros(tf.shape(ciphertext)[0], dtype=tf.int64)
    self._exponent = exponent
    return self

  def _strings_like(self, inputs, origin_inp):
    inputs = tf.constant(str(inputs), dtype=tf.string, shape=[1] * len(origin_inp.get_shape()))
    inputs = tf.tile(inputs, tf.shape(origin_inp))
    return inputs

  def decrypt(self, private_key):

    def l_fn(x, p, hp):
      ones = self._strings_like(1, x)
      p = self._strings_like(p, x)
      hp = self._strings_like(hp, x)
      r = fed_ops.gmp_sub(x, ones)
      r = fed_ops.gmp_div(r, p)
      r = fed_ops.gmp_mul(r, hp)
      r = fed_ops.gmp_mod(r, p)
      return r

    def crt(mp, mq, private_key):
      q_inv = self._strings_like(private_key.q_inverse, mp)
      q = self._strings_like(private_key.q, mp)
      p = self._strings_like(private_key.p, mp)
      n = self._strings_like(self.public_key.n, mp)
      u = fed_ops.gmp_sub(mp, mq)
      u = fed_ops.gmp_mul(u, q_inv)
      u = fed_ops.gmp_mod(u, p)
      x = fed_ops.gmp_mul(u, q)
      x = fed_ops.gmp_add(mq, x)
      x = fed_ops.gmp_mod(x, n)
      return x

    private_p_1 = self._strings_like(private_key.p - 1, self._ciphertext)
    private_psquare = self._strings_like(private_key.psquare, self._ciphertext)
    private_q_1 = self._strings_like(private_key.q - 1, self._ciphertext)
    private_qsquare = self._strings_like(private_key.qsquare, self._ciphertext)
    p = fed_ops.gmp_pow_mod(self._ciphertext, private_p_1, private_psquare)
    mp = l_fn(p, private_key.p, private_key.hp)
    q = fed_ops.gmp_pow_mod(self._ciphertext, private_q_1, private_qsquare)
    mq = l_fn(q, private_key.q, private_key.hq)
    encoded = crt(mp, mq, private_key)
    fp = FixedPointTensor(self.public_key.n, self.public_key.max_int)
    fp.set_encoding(encoded, self._exponent)
    decrypt_value = fp.decode()
    return decrypt_value

  @property
  def exponent(self):
    return self._exponent

  @property
  def public_key(self):
    return self._public_key

  @property
  def ciphertext(self):
    return self._ciphertext

  def _add_raw(self, raw):
    public_nsquare = self._strings_like(self.public_key.nsquare, self._ciphertext)
    ciphertext = fed_ops.gmp_mul(self._ciphertext, raw)
    ciphertext = fed_ops.gmp_mod(ciphertext, public_nsquare)
    return ciphertext

  def add_scalar(self, scalar):
    fp = FixedPointTensor(self.public_key.n, self.public_key.max_int)
    fp = fp.encode(scalar, max_exponent=self._exponent)
    scalar_encoding = fp.encoding
    cipher = self._raw_encrypt(scalar_encoding)
    cipher = self._add_raw(cipher)
    self._ciphertext = cipher
    return self

  def _pos_matrix(self, ciphertext):
    max_int = self._strings_like(self.public_key.max_int, ciphertext)
    cmp_result = fed_ops.gmp_cmp(ciphertext, max_int)
    pos_matrix = tf.less_equal(cmp_result, 0)
    return pos_matrix

  def mul_scalar(self, scalar):
    public_nsquare = self._strings_like(self.public_key.nsquare, self._ciphertext)
    public_n = self._strings_like(self.public_key.n, self._ciphertext)
    fp = FixedPointTensor(self.public_key.n, self.public_key.max_int)
    fp = fp.encode(scalar)

    pos_matrix = self._pos_matrix(self._ciphertext)
    cipher = tf.where(pos_matrix, self._ciphertext,
                      fed_ops.gmp_invert(self._ciphertext, public_nsquare))
    scalar_cipher = tf.where(pos_matrix, fp.encoding,
                             fed_ops.gmp_sub(public_n, fp.encoding))

    ciphertext = fed_ops.gmp_pow_mod(cipher, scalar_cipher, public_nsquare)
    self._ciphertext = ciphertext
    self._exponent = self._exponent + fp.exponent
    return self
