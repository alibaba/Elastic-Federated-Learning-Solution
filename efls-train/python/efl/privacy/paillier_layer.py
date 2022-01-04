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

from efl import exporter
from efl.privacy.paillier import fixedpoint_encode
from efl.privacy.paillier import FixedPointTensor, PaillierTensor

@exporter.export('paillier.sender.Dense')
class PaillierActiveDense(tf.layers.Dense):
  def __init__(self, keypair, communicator, prefix, units, name=None, _reuse=None):
    super(PaillierActiveDense, self).__init__(
        units, use_bias=False, kernel_initializer='zeros', trainable=False, name=name, _reuse=_reuse)
    self._keypair = keypair
    self._communicator = communicator
    self._prefix = prefix

  def call(self, inputs):
    @tf.custom_gradient
    def compute(inputs, w):
      def grad(dy):
        shape = w.shape
        nw = fixedpoint_encode(w)
        nw.mantissa = self._keypair.encrypt(nw.mantissa)
        nf = tf.random.normal(shape=shape, mean=10*tf.sigmoid(tf.reduce_sum(inputs)))
        with tf.control_dependencies([dy]):
          dw_add_n2_mantissa = self._communicator.recv(self._prefix + '_[dw+n2]_mantissa',
                                                       shape=shape, dtype=tf.string)
          dw_add_n2_exponent = self._communicator.recv(self._prefix + '_[dw+n2]_exponent',
                                                       shape=shape, dtype=tf.int64)
          send_nw_mantissa = self._communicator.send(self._prefix + '_[nw]_mantissa', nw.mantissa.tensor)
          send_nw_exponent = self._communicator.send(self._prefix + '_[nw]_exponent', nw.exponent)
        dw_add_n2_mantissa = self._keypair.decrypt(dw_add_n2_mantissa)
        dw_add_n2 = FixedPointTensor(dw_add_n2_mantissa, dw_add_n2_exponent).decode()
        dw_add_n2 = dw_add_n2 + nf
        send_dw_add_n2 = self._communicator.send(self._prefix + '_dw+n2', dw_add_n2)
        with tf.control_dependencies([send_nw_mantissa, send_nw_exponent]):
          shape = inputs.shape.as_list()
          shape = [-1 if dim is None else dim for dim in shape]
          dx_mantissa = self._communicator.recv(self._prefix + '_[dx]_mantissa', shape=shape, dtype=tf.string)
          dx_exponent = self._communicator.recv(self._prefix + '_[dx]_exponent', shape=shape, dtype=tf.int64)
        dx_mantissa = self._keypair.decrypt(dx_mantissa)
        dx = FixedPointTensor(dx_mantissa, dx_exponent).decode()
        with tf.control_dependencies([send_dw_add_n2]):
          return dx, -nf

      x = fixedpoint_encode(inputs)
      x.mantissa = self._keypair.encrypt(x.mantissa)
      send_x_mantissa = self._communicator.send(self._prefix + '_[x]_mantissa', x.mantissa.tensor)
      send_x_exponent = self._communicator.send(self._prefix + '_[x]_exponent', x.exponent)
      z_add_n1 = inputs @ w
      with tf.control_dependencies([send_x_mantissa, send_x_exponent]):
        shape = z_add_n1.shape.as_list()
        shape = [-1 if dim is None else dim for dim in shape]
        z_add_n1_mantissa = self._communicator.recv(self._prefix + '_[z+n1]_mantissa', shape=shape, dtype=tf.string)
        z_add_n1_exponent = self._communicator.recv(self._prefix + '_[z+n1]_exponent', shape=shape, dtype=tf.int64)
      z_add_n1_mantissa = self._keypair.decrypt(z_add_n1_mantissa)
      z_add_n1 = z_add_n1 + FixedPointTensor(z_add_n1_mantissa, z_add_n1_exponent).decode()
      send_z_add_n1 = self._communicator.send(self._prefix + '_z+n1', z_add_n1)
      with tf.control_dependencies([send_z_add_n1]):
        return tf.identity(z_add_n1), grad

    rank = len(inputs.shape)
    if rank > 2:
      raise ValueError('PaillierDense hasn\'t support broadcasting yet.')
    else:
      outputs = compute(inputs, self.kernel)
    return outputs


@exporter.export('paillier.sender.dense')
def dense_send(inputs, keypair, communicator, prefix, units,
               name=None, reuse=None):
  layer = PaillierActiveDense(keypair, communicator, prefix, units,
                              name=name, _reuse=reuse)
  return layer.apply(inputs), layer.kernel


@exporter.export('paillier.recver.Dense')
class PaillierPassiveDense(tf.layers.Dense):
  def __init__(self, keypair, communicator, prefix, units,
               kernel_initializer=None,
               name=None,
               dtype=None,
               _scope=None,
               _reuse=None):
    super(PaillierPassiveDense, self).__init__(units=units,
        use_bias=False,
        kernel_initializer=kernel_initializer,
        trainable=False,
        name=name,
        dtype=dtype,
        _scope=_scope,
        _reuse=_reuse)
    self._keypair = keypair
    self._communicator = communicator
    self._prefix = prefix

  def call(self, inputs):
    @tf.custom_gradient
    def compute(inputs, w):
      x_exponent = inputs
      shape = [-1 if dim is None else dim for dim in inputs.shape.as_list()]
      x_mantissa = self._communicator.recv(self._prefix + '_[x]_mantissa', shape=shape, dtype=tf.string)
      def grad(dy):
        fpdy = fixedpoint_encode(dy, decrease_precision=True)
        xt = FixedPointTensor(PaillierTensor(self._keypair, tf.transpose(x_mantissa)), tf.transpose(x_exponent))
        dw = xt @ fpdy
        n2 = tf.random.normal(shape=w.shape)
        dw_add_n2 = dw + n2
        send_dw_add_n2_mantissa = self._communicator.send(self._prefix + '_[dw+n2]_mantissa', dw_add_n2.mantissa.tensor)
        send_dw_add_n2_exponent = self._communicator.send(self._prefix + '_[dw+n2]_exponent', dw_add_n2.exponent)
        with tf.control_dependencies([send_dw_add_n2_mantissa, send_dw_add_n2_exponent]):
          dw_add_n2 = self._communicator.recv(self._prefix + '_dw+n2', shape=w.shape)
          dw = dw_add_n2 - n2
        dx = dy @ tf.transpose(w)
        with tf.control_dependencies([dy]):
          nw_mantissa = self._communicator.recv(self._prefix + '_[nw]_mantissa', shape=w.shape, dtype=tf.string)
          nw_exponent = self._communicator.recv(self._prefix + '_[nw]_exponent', shape=w.shape, dtype=tf.int64)
        nw = FixedPointTensor(PaillierTensor(self._keypair, nw_mantissa), nw_exponent)
        fp = nw @ FixedPointTensor(tf.transpose(fpdy.mantissa), tf.transpose(fpdy.exponent))
        fp = FixedPointTensor(PaillierTensor(self._keypair, tf.transpose(fp.mantissa.tensor)),
                              tf.transpose(fp.exponent))
        dx = fp + dx
        send_dx_mantissa = self._communicator.send(self._prefix + '_[dx]_mantissa', dx.mantissa.tensor)
        send_dx_exponent = self._communicator.send(self._prefix + '_[dx]_exponent', dx.exponent)
        with tf.control_dependencies([send_dx_mantissa, send_dx_exponent]):
          return tf.zeros_like(inputs), dw

      x = FixedPointTensor(PaillierTensor(self._keypair, x_mantissa), x_exponent)
      z = x @ fixedpoint_encode(w, decrease_precision=True)
      n1 = tf.random.normal(shape=tf.shape(z.exponent))
      z_add_n1 = z + n1
      send_z_add_n1_mantissa = self._communicator.send(self._prefix + '_[z+n1]_mantissa', z_add_n1.mantissa.tensor)
      send_z_add_n1_exponent = self._communicator.send(self._prefix + '_[z+n1]_exponent', z_add_n1.exponent)
      with tf.control_dependencies([send_z_add_n1_mantissa, send_z_add_n1_exponent]):
        shape = [-1 if dim is None else dim for dim in z.exponent.shape.as_list()]
        z_add_n1 = self._communicator.recv(self._prefix + '_z+n1', shape=shape)
        return z_add_n1 - n1, grad

    rank = len(inputs.shape)
    if rank > 2:
      raise ValueError('PaillierDense hasn\'t support broadcasting yet.')
    else:
      outputs = compute(inputs, self.kernel)
    return outputs


@exporter.export('paillier.recver.dense')
def dense_recv(inputs, keypair, communicator, prefix, recv_shape, units,
               activation=None,
               use_bias=True,
               kernel_initializer=None,
               bias_initializer=tf.zeros_initializer(),
               kernel_regularizer=None,
               bias_regularizer=None,
               activity_regularizer=None,
               kernel_constraint=None,
               bias_constraint=None,
               trainable=True,
               name=None,
               reuse=None):
  paillier_name = None if name is None else 'paillier_' + name
  paillier_layer = PaillierPassiveDense(keypair, communicator, prefix, units,
                                        kernel_initializer=kernel_initializer,
                                        name=paillier_name,
                                        dtype=tf.float32,
                                        _scope=paillier_name,
                                        _reuse=reuse)

  x_exponent = communicator.recv(prefix + '_[x]_exponent', shape=recv_shape, dtype=tf.int64)
  y = paillier_layer.apply(x_exponent)

  if inputs is not None:
    y = y + tf.layers.Dense(units,
                            use_bias=use_bias,
                            kernel_initializer=kernel_initializer,
                            bias_initializer=bias_initializer,
                            kernel_regularizer=kernel_regularizer,
                            bias_regularizer=bias_regularizer,
                            kernel_constraint=kernel_constraint,
                            bias_constraint=bias_constraint,
                            trainable=trainable,
                            name=name,
                            _scope=name,
                            _reuse=reuse).apply(inputs)

  return tf.keras.layers.Activation(activation=activation,
                                    activity_regularizer=activity_regularizer).apply(y), paillier_layer.kernel


@exporter.export('paillier.sender.Weight')
class PaillierActiveWeight():
  def __init__(self, keypair, communicator, prefix, units):
    self._keypair = keypair
    self._communicator = communicator
    self._prefix = prefix
    self.kernel = tf.get_variable(prefix + '_kernel', (units,), dtype=tf.float32, initializer=tf.zeros_initializer(), trainable=False)

  def call(self, inputs):
    @tf.custom_gradient
    def compute(inputs, w):
      def grad(dy):
        shape = w.shape
        nw = fixedpoint_encode(w)
        nw.mantissa = self._keypair.encrypt(nw.mantissa)
        nf = tf.random.normal(shape=shape, mean=10*tf.sigmoid(tf.reduce_sum(inputs)))
        with tf.control_dependencies([dy]):
          dw_add_n2_mantissa = self._communicator.recv(self._prefix + '_[dw+n2]_mantissa',
                                                       shape=shape, dtype=tf.string)
          dw_add_n2_exponent = self._communicator.recv(self._prefix + '_[dw+n2]_exponent',
                                                       shape=shape, dtype=tf.int64)
          send_nw_mantissa = self._communicator.send(self._prefix + '_[nw]_mantissa', nw.mantissa.tensor)
          send_nw_exponent = self._communicator.send(self._prefix + '_[nw]_exponent', nw.exponent)
        dw_add_n2_mantissa = self._keypair.decrypt(dw_add_n2_mantissa)
        dw_add_n2 = FixedPointTensor(dw_add_n2_mantissa, dw_add_n2_exponent).decode()
        dw_add_n2 = dw_add_n2 + nf
        send_dw_add_n2 = self._communicator.send(self._prefix + '_dw+n2', dw_add_n2)
        with tf.control_dependencies([send_nw_mantissa, send_nw_exponent]):
          shape = inputs.shape.as_list()
          shape = [-1 if dim is None else dim for dim in shape]
          dx_mantissa = self._communicator.recv(self._prefix + '_[dx]_mantissa', shape=shape, dtype=tf.string)
          dx_exponent = self._communicator.recv(self._prefix + '_[dx]_exponent', shape=shape, dtype=tf.int64)
        dx_mantissa = self._keypair.decrypt(dx_mantissa)
        dx = FixedPointTensor(dx_mantissa, dx_exponent).decode()
        with tf.control_dependencies([send_dw_add_n2]):
          return dx, -nf

      x = fixedpoint_encode(inputs)
      x.mantissa = self._keypair.encrypt(x.mantissa)
      send_x_mantissa = self._communicator.send(self._prefix + '_[x]_mantissa', x.mantissa.tensor)
      send_x_exponent = self._communicator.send(self._prefix + '_[x]_exponent', x.exponent)
      z_add_n1 = inputs * w
      with tf.control_dependencies([send_x_mantissa, send_x_exponent]):
        shape = z_add_n1.shape.as_list()
        shape = [-1 if dim is None else dim for dim in shape]
        z_add_n1_mantissa = self._communicator.recv(self._prefix + '_[z+n1]_mantissa', shape=shape, dtype=tf.string)
        z_add_n1_exponent = self._communicator.recv(self._prefix + '_[z+n1]_exponent', shape=shape, dtype=tf.int64)
      z_add_n1_mantissa = self._keypair.decrypt(z_add_n1_mantissa)
      z_add_n1 = z_add_n1 + FixedPointTensor(z_add_n1_mantissa, z_add_n1_exponent).decode()
      send_z_add_n1 = self._communicator.send(self._prefix + '_z+n1', z_add_n1)
      with tf.control_dependencies([send_z_add_n1]):
        return tf.identity(z_add_n1), grad

    rank = len(inputs.shape)
    if rank > 2:
      raise ValueError('PaillierDense hasn\'t support broadcasting yet.')
    else:
      outputs = compute(inputs, self.kernel)
    return outputs

  def apply(self, inputs):
    return self.call(inputs)


@exporter.export('paillier.sender.weight')
def weight_send(inputs, keypair, communicator, prefix, units):
  layer = PaillierActiveWeight(keypair, communicator, prefix, units)
  return layer.apply(inputs), layer.kernel


@exporter.export('paillier.recver.Weight')
class PaillierPassiveWeight():
  def __init__(self, keypair, communicator, prefix, units, kernel_initializer=None):
    self._keypair = keypair
    self._communicator = communicator
    self._prefix = prefix
    if kernel_initializer is None:
      kernel_initializer = tf.zeros_initializer()
    self.kernel = tf.get_variable(prefix + '_kernel', (units,), dtype=tf.float32, initializer=kernel_initializer, trainable=False)

  def call(self, inputs):
    @tf.custom_gradient
    def compute(inputs, w):
      x_exponent = inputs
      shape = [-1 if dim is None else dim for dim in inputs.shape.as_list()]
      x_mantissa = self._communicator.recv(self._prefix + '_[x]_mantissa', shape=shape, dtype=tf.string)
      x = FixedPointTensor(PaillierTensor(self._keypair, x_mantissa), x_exponent)

      def grad(dy):
        dw = x * fixedpoint_encode(dy, decrease_precision=True)
        sum_mantissa = dw.mantissa.tensor[0]
        sum_exponent = dw.exponent[0]
        keypair = dw.mantissa.keypair
        cond = lambda i, m, e: tf.less(i, tf.shape(inputs)[0])
        def body(i, m, e):
          fp = FixedPointTensor(PaillierTensor(keypair, m), e) +\
               FixedPointTensor(PaillierTensor(keypair, dw.mantissa.tensor[i]), dw.exponent[i])
          m = fp.mantissa.tensor
          e = fp.exponent
          return tf.add(i, 1), m, e
        _, m, e = tf.while_loop(cond=cond, body=body, loop_vars=[tf.constant(1), sum_mantissa, sum_exponent])
        dw = FixedPointTensor(PaillierTensor(keypair, m), e)
        n2 = tf.random.normal(shape=w.shape)
        dw_add_n2 = dw + n2
        send_dw_add_n2_mantissa = self._communicator.send(self._prefix + '_[dw+n2]_mantissa', dw_add_n2.mantissa.tensor)
        send_dw_add_n2_exponent = self._communicator.send(self._prefix + '_[dw+n2]_exponent', dw_add_n2.exponent)
        with tf.control_dependencies([send_dw_add_n2_mantissa, send_dw_add_n2_exponent]):
          dw_add_n2 = self._communicator.recv(self._prefix + '_dw+n2', shape=w.shape)
          dw = dw_add_n2 - n2
        dx = dy * w
        with tf.control_dependencies([dy]):
          nw_mantissa = self._communicator.recv(self._prefix + '_[nw]_mantissa', shape=w.shape, dtype=tf.string)
          nw_exponent = self._communicator.recv(self._prefix + '_[nw]_exponent', shape=w.shape, dtype=tf.int64)
        nw = FixedPointTensor(PaillierTensor(self._keypair, nw_mantissa), nw_exponent)
        dx = nw * dy + dx
        send_dx_mantissa = self._communicator.send(self._prefix + '_[dx]_mantissa', dx.mantissa.tensor)
        send_dx_exponent = self._communicator.send(self._prefix + '_[dx]_exponent', dx.exponent)
        with tf.control_dependencies([send_dx_mantissa, send_dx_exponent]):
          return tf.zeros_like(inputs), dw

      z = x * fixedpoint_encode(w, decrease_precision=True)
      n1 = tf.random.normal(shape=tf.shape(z.exponent))
      z_add_n1 = z + n1
      send_z_add_n1_mantissa = self._communicator.send(self._prefix + '_[z+n1]_mantissa', z_add_n1.mantissa.tensor)
      send_z_add_n1_exponent = self._communicator.send(self._prefix + '_[z+n1]_exponent', z_add_n1.exponent)
      with tf.control_dependencies([send_z_add_n1_mantissa, send_z_add_n1_exponent]):
        z_add_n1 = self._communicator.recv(self._prefix + '_z+n1', shape=shape)
        return z_add_n1 - n1, grad

    rank = len(inputs.shape)
    if rank > 2:
      raise ValueError('PaillierDense hasn\'t support broadcasting yet.')
    else:
      outputs = compute(inputs, self.kernel)
    return outputs

  def apply(self, inputs):
    return self.call(inputs)


@exporter.export('paillier.recver.weight')
def weight_recv(inputs, keypair, communicator, prefix, units,
                kernel_initializer=None):
  paillier_layer = PaillierPassiveWeight(keypair, communicator, prefix, units,
                                         kernel_initializer=kernel_initializer)

  x_exponent = communicator.recv(prefix + '_[x]_exponent', shape=[-1, units], dtype=tf.int64)
  y = paillier_layer.apply(x_exponent)
  if inputs is not None:
    y = y + inputs

  return y, paillier_layer.kernel

