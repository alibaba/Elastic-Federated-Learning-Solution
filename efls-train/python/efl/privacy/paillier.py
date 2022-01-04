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
from tensorflow.python.training import session_run_hook

from efl import exporter
from efl.lib import ops as fed_ops
from enum import Enum

from efl.privacy.encryptor_utils import Role

@exporter.export('paillier.Tensor')
class PaillierTensor(object):
  def __init__(self, keypair, tensor):
    self.keypair = keypair
    self.tensor = tensor

  def __add__(self, another):
    if not isinstance(another, PaillierTensor):
      another = self.keypair.encrypt(another)
    return PaillierTensor(self.keypair,
                          self.keypair.add(self.tensor, another.tensor))

  def __mul__(self, scalar):
    return PaillierTensor(self.keypair,
                          self.keypair.mul_scalar(self.tensor, scalar))

  def decrypt(self, dtype=tf.string):
    return self.keypair.decrypt(self, dtype)

  def __lshift__(self, exp):
    return PaillierTensor(self.keypair,
                          self.keypair.mul_exp2(self.tensor, exp))


@exporter.export('paillier.Keypair')
class PaillierKeypair(object):
  def __init__(self):
    self._handler = fed_ops.paillier_keypair_handle_op()

  def encrypt(self, plaintext, hsa=None):
    if hsa is None:
      hsa = tf.as_string(tf.zeros_like(plaintext, dtype=tf.int64))
    return PaillierTensor(self, fed_ops.paillier_encrypt(self._handler, plaintext, hsa))

  def decrypt(self, paillier_tensor, dtype=tf.string):
    if not isinstance(paillier_tensor, PaillierTensor):
      return fed_ops.paillier_decrypt(self._handler, paillier_tensor, dtype=dtype)
    else:
      return fed_ops.paillier_decrypt(self._handler, paillier_tensor.tensor, dtype=dtype)

  def set_public_key(self, n, n_bytes, hs, a_bytes, group_size=None):
    return fed_ops.set_paillier_public_key(self._handler, n, n_bytes, hs, a_bytes, group_size=None)

  def set_private_key(self, p, q):
    return fed_ops.set_paillier_private_key(self._handler, p, q)

  def add(self, x, y):
    shape = tf.broadcast_dynamic_shape(tf.shape(x), tf.shape(y))
    x = tf.broadcast_to(x, shape=shape)
    y = tf.broadcast_to(y, shape=shape)
    return fed_ops.paillier_add(self._handler, x, y)

  def mul_scalar(self, x, scalar):
    shape = tf.broadcast_dynamic_shape(tf.shape(x), tf.shape(scalar))
    x = tf.broadcast_to(x, shape=shape)
    scalar = tf.broadcast_to(scalar, shape=shape)
    return fed_ops.paillier_mul_scalar(self._handler, x, scalar)

  def mul_exp2(self, x, exp):
    shape = tf.broadcast_dynamic_shape(tf.shape(x), tf.shape(exp))
    x = tf.broadcast_to(x, shape=shape)
    exp = tf.broadcast_to(exp, shape=shape)
    return fed_ops.paillier_mul_exp2(self._handler, x, exp)

  def matmul(self, xm, xe, ym, ye):
    return fed_ops.paillier_matmul(self._handler, xm, xe, ym, ye)

  def invert(self, x):
    return fed_ops.paillier_invert(self._handler, x)

  def initialize(self):
    return fed_ops.create_paillier_keypair(self._handler)

  def generate_keypair(self, n_bytes=None, reps=None, a_bytes=None, group_size=None):
    return fed_ops.generate_paillier_keypair(self._handler, n_bytes=n_bytes, reps=reps,
                                             a_bytes=a_bytes, group_size=group_size)


@exporter.export('paillier.fixedpoint.Tensor')
class FixedPointTensor(object):
  def __init__(self, mantissa, exponent):
    self.mantissa = mantissa
    self.exponent = exponent

  def decode(self, dtype=tf.float32):
    return fed_ops.fixed_point_to_float_point(self.mantissa, self.exponent, dtype=dtype)

  def __add__(self, another):
    if not isinstance(another, FixedPointTensor):
      another = fixedpoint_encode(another)
    exponent = tf.minimum(self.exponent, another.exponent)
    d = self.exponent - another.exponent
    dl = tf.maximum(d, 0)
    dr = tf.abs(tf.minimum(d, 0))
    if not isinstance(self.mantissa, PaillierTensor):
      self_mantissa = another.mantissa.keypair.encrypt(self.mantissa)
      another_mantissa = another.mantissa
    elif not isinstance(another.mantissa, PaillierTensor):
      self_mantissa = self.mantissa
      another_mantissa = self.mantissa.keypair.encrypt(another.mantissa)
    else:
      self_mantissa = self.mantissa
      another_mantissa = another.mantissa
    mantissa = (self_mantissa << dl) + (another_mantissa << dr)
    return FixedPointTensor(mantissa, exponent)

  def __mul__(self, another):
    if not isinstance(another, FixedPointTensor):
      another = fixedpoint_encode(another)
    return FixedPointTensor(self.mantissa * another.mantissa, self.exponent + another.exponent)

  def __matmul__(self, another):
    if not isinstance(another, FixedPointTensor):
      another = fixedpoint_encode(another)
    keypair = self.mantissa.keypair
    mantissa, exponent = keypair.matmul(self.mantissa.tensor, self.exponent, another.mantissa, another.exponent)
    return FixedPointTensor(PaillierTensor(keypair, mantissa), exponent)


@exporter.export('paillier.fixedpoint.encode')
def fixedpoint_encode(t, decrease_precision=None):
  return FixedPointTensor(*fed_ops.convert_to_fixed_point(t, decrease_precision=decrease_precision))


@exporter.export('paillier.fixedpoint.decode')
def fixedpoint_decode(fp, dtype=tf.float32):
  return fed_ops.fixed_point_to_float_point(fp.mantissa, fp.exponent, dtype=dtype)


@exporter.export('paillier.Hook')
class PaillierHook(session_run_hook.SessionRunHook):
  def __init__(self,
               keypair,
               communicator,
               role,
               prefix,
               update_step_interval=None,
               n_bytes=None,
               a_bytes=None,
               reps=None,
               group_size=None):
    self._local_step = 0
    self._init_op = keypair.initialize()
    self._update_step_interval = update_step_interval
    if n_bytes is None:
      n_bytes = 512
    if a_bytes is None:
      a_bytes = n_bytes // 2
    if role == Role.SENDER:
      public_key, _ = keypair.generate_keypair(n_bytes=n_bytes, a_bytes=a_bytes, reps=reps, group_size=group_size)
      send_public_key = communicator.send(prefix + '_public_key', public_key)
      send_n_bytes = communicator.send(prefix + '_bytes', tf.convert_to_tensor([n_bytes], dtype=tf.int32))
      self._update_op = tf.group([send_public_key, send_n_bytes])
    elif role == Role.RECEIVER:
      recv_public_key = communicator.recv(prefix + '_public_key', shape=(2,), dtype=tf.string)
      recv_n_bytes = communicator.recv(prefix + '_bytes', dtype=tf.int32)
      self._update_op = keypair.set_public_key(recv_public_key[0], recv_n_bytes, recv_public_key[1],
                                               tf.convert_to_tensor([a_bytes]), group_size=group_size)
    else:
      raise ValueError(str(role) + ': No such role.')

  def after_create_session(self, sess, coord):
    sess.run(self._init_op)
    if self._update_step_interval is None:
      sess.run(self._update_op)

  def before_run(self, run_context):
    if self._update_step_interval is not None and self._local_step % self._update_step_interval == 0:
      self._local_step = 0
      run_context.session.run(self._update_op)

  def after_run(self, run_context, run_values):
    if self._update_step_interval is not None:
      self._local_step += 1

  def end(self, sess):
    pass

