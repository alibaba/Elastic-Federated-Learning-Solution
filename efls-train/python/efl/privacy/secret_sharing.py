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
from efl.privacy.encryptor_utils import Role
from efl.privacy.encryptor_utils import SecretSharingMatmulMode as Mode
from efl import exporter


def generate_suitable_noise(t):
  return tf.random.uniform(tf.shape(t)) * t


def _matmul(a, b, communicator, name, mode):
  if mode == Mode.A:
    e = generate_suitable_noise(a)
    e_odd, e_even = e[:, 1::2], e[:, ::2]
    e1 = e_even + e_odd
    a1 = a + e
    send_a1_and_e1 = communicator.send(name + '_a1_and_e1', tf.concat([a1, e1], axis=1))
    with tf.control_dependencies([a]):
      b1_and_f1 = communicator.recv(name + '_b1_and_f1', shape=[b[0] * 3 // 2, b[1]], dtype=a.dtype)
    b1, f1 = b1_and_f1[:b[0]], b1_and_f1[b[0]:]
    with tf.control_dependencies([send_a1_and_e1]):
      z = (a - e) @ b1 + (e_odd - e_even) @ f1
  elif mode == Mode.B:
    f = generate_suitable_noise(b)
    f_odd, f_even = f[1::2], f[::2]
    f1 = f_even - f_odd
    b1 = b / 2 - f
    send_b1_and_f1 = communicator.send(name + '_b1_and_f1', tf.concat([b1, f1], axis=0))
    with tf.control_dependencies([b]):
      a1_and_e1 = communicator.recv(name + '_a1_and_e1', shape=[a[0], a[1] * 3 // 2], dtype=b.dtype)
    a1, e1 = a1_and_e1[:, :a[1]], a1_and_e1[:, a[1]:]
    with tf.control_dependencies([send_b1_and_f1]):
      z = a1 @ (b / 2 + f) - e1 @ (f_odd + f_even)
  elif mode == Mode.C:
    if a.dtype != b.dtype:
      raise TypeError('The dtypes of a and b must be the same.')
    shape_a = tf.shape(a)
    shape_b = tf.shape(b)
    e = generate_suitable_noise(a)
    f = generate_suitable_noise(b)
    z = a @ b
    e_odd, e_even = e[:, 1::2], e[:, ::2]
    f_odd, f_even = f[1::2], f[::2]
    e1 = e_even + e_odd
    f1 = f_even - f_odd
    a1 = a + e
    b1 = b / 2 - f
    send_tensor = tf.concat([tf.concat([a1, e1], axis=1), tf.transpose(tf.concat([b1, f1], axis=0))], axis=0)
    send_a1_e1_b1_f1 = communicator.send(name + '_a1_e1_b1_f1', send_tensor)
    with tf.control_dependencies([a, b]):
      recv = communicator.recv(name + '_a1_e1_b1_f1', shape=[shape_a[0] + shape_b[1], shape_a[1] * 3 // 2], dtype=a.dtype)
    a1_e1, b1_f1 = recv[:shape_a[0]], tf.transpose(recv[shape_a[0]:])
    ra1, re1 = a1_e1[:, :shape_a[1]], a1_e1[:, shape_a[1]:]
    rb1, rf1 = b1_f1[:shape_b[0]], b1_f1[shape_b[0]:]
    with tf.control_dependencies([send_a1_e1_b1_f1]):
      z1 = (a - e) @ rb1 + (e_odd - e_even) @ rf1
      z2 = ra1 @ (b / 2 +  f) - re1 @ (f_odd + f_even)
      z = z + z1 + z2
  else:
    raise ValueError(str(mode) + ': No such mode.')
  return z


@exporter.export('secret_sharing.matmul')
def matmul(a, b, communicator, name, mode, combine_gradients=False):
  @tf.custom_gradient
  def compute(a, b):
    def grad(dy):
      if mode == Mode.A:
        raise ValueError('Please switch from mode A to mode C, because mode A is equivalent to mode C when the gradients need to be computed.')
      elif mode == Mode.B:
        raise ValueError('Please switch from mode B to mode C, because mode B is equivalent to mode C when the gradients need to be computed.')
      elif mode == Mode.C:
        if combine_gradients:
          shape_dy = tf.shape(dy)
          shape_a = tf.shape(a)
          zeros = tf.zeros(shape=[shape_dy[0], shape_dy[0]], dtype=dy.dtype)
          dy_at = tf.concat([tf.concat([dy, zeros], axis=1),
                             tf.concat([tf.zeros_like(b), tf.transpose(a)], axis=1)], axis=0)
          zeros = tf.zeros(shape=[shape_dy[1], shape_dy[1]], dtype=dy.dtype)
          bt_dy = tf.concat([tf.concat([tf.transpose(b), zeros], axis=1),
                             tf.concat([tf.zeros_like(a), dy], axis=1)], axis=0)
          with tf.control_dependencies([dy]):
            da_db = _matmul(dy_at, bt_dy, communicator, name + '_gradient', mode)
          da = da_db[:shape_a[0], :shape_a[1]]
          db = da_db[-shape_a[1]:, -shape_dy[1]:]
        else:
          da = _matmul(dy, tf.transpose(b), communicator, name + '_da', mode)
          db = _matmul(tf.transpose(a), dy, communicator, name + '_db', mode)
        return da, db
      else:
        raise ValueError(str(mode) + ': No such mode.')
    return _matmul(a, b, communicator, name, mode), grad
  return compute(a, b)


@exporter.export('secret_sharing.Dense')
class SecretSharingDense(tf.layers.Dense):
  def __init__(self, communicator, prefix, units, noise_divisor=None, combine_gradients=False, **kwargs):
    super(SecretSharingDense, self).__init__(units, **kwargs) 
    self._communicator = communicator
    self._prefix = prefix
    self._noise_divisor = noise_divisor
    self._combine_gradients = combine_gradients

  def call(self, inputs):
    rank = len(inputs.shape)
    if rank > 2:
      raise ValueError('SecretSharingDense hasn\'t support broadcasting yet.')
    else:
      if self._noise_divisor is not None:
        noise = generate_suitable_noise(self.kernel.value()) / self._noise_divisor
        send = self._communicator.send(self._prefix + '_weights', self.kernel - noise)
        peer_kernel = self._communicator.recv(self._prefix + '_weights', shape=self.kernel.shape, dtype=self.kernel.dtype)
        with tf.control_dependencies([send]):
          self.kernel = (self.kernel + noise + peer_kernel) / 2
      outputs = matmul(inputs, self.kernel, self._communicator, self._prefix, Mode.C, combine_gradients=self._combine_gradients)
    if self.use_bias:
      outputs += self.bias
    return outputs


@exporter.export('secret_sharing.dense')
def dense(inputs, communicator, prefix, units, noise_divisor=None, combine_gradients=False, **kwargs):
  return SecretSharingDense(communicator, prefix, units, noise_divisor=noise_divisor, combine_gradients=combine_gradients, **kwargs).apply(inputs)


@exporter.export('secret_sharing.share')
def share(inputs, communicator, name):
  @tf.custom_gradient
  def compute(inputs):
    def grad(dy):
      with tf.control_dependencies(dy):
        return dy + communicator.recv(name + '_grad', shape=tf.shape(dy), dtype=dy.dtype)
    a = generate_suitable_noise(inputs)
    send = communicator.send(name, a)
    with tf.control_dependencies([send]):
      return inputs - a, grad
  return compute(inputs)


@exporter.export('secret_sharing.reveal')
def reveal(inputs, communicator, name, role):
  @tf.custom_gradient
  def compute(inputs):
    def grad(dy):
      if role == Role.RECEIVER:
        a = generate_suitable_noise(dy)
        send = communicator.send(name + '_grad', a)
        with tf.control_dependencies([send]):
          return dy - a
      elif role == Role.SENDER:
        with tf.control_dependencies([dy]):
          return communicator.recv(name + '_grad', shape=tf.shape(dy), dtype=dy.dtype)
      else:
        raise ValueError(str(role) + ': No such role.')
    if role == Role.SENDER:
      send_inputs = communicator.send(name, inputs)
      with tf.control_dependencies([send_inputs]):
        return tf.identity(inputs), grad
    elif role == Role.RECEIVER:
      return inputs + communicator.recv(name, shape=tf.shape(inputs), dtype=inputs.dtype), grad
    else:
      raise ValueError(str(role) + ': No such role.')
  return compute(inputs)
