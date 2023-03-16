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

from efl import exporter
from efl.privacy.encrypt import PaillierEncrypt, PaillierPublicKey
from efl.privacy.paillier_tensor import PaillierTensor

@exporter.export("privacy.EncryptActiveLayer")
class EncryptActiveLayer():
  def __init__(self, communicator, dim, public_file, private_file, learning_rate=0.01, noise_initializer=None, update_noise=True, name='hetero'):
    self._comm = communicator
    self._dim = dim
    self._learning_rate = learning_rate
    self._name = name
    self._encrypt = PaillierEncrypt()
    self._update_noise = update_noise
    self._encrypt.load_key_from_file(public_file, private_file)
    if noise_initializer is None:
      noise_initializer = tf.constant_initializer(1e-9)
    self._forward_noise = tf.get_variable(self._name + '_dense_noise', [1, dim], dtype=tf.float32, initializer=noise_initializer, trainable=False)

  def compute(self, inputs):
    @tf.custom_gradient
    def tf_compute(inputs):
      paillier = PaillierTensor(self._encrypt.public_key)
      paillier = paillier.encrypt(inputs)
      send_encrypt_cipher = self._comm.send(self._name + "_encrypt_cipher", paillier.ciphertext)
      send_encrypt_exponent = self._comm.send(self._name + "_encrypt_exponent", paillier.exponent)
      with tf.control_dependencies([send_encrypt_cipher, send_encrypt_exponent]):
        encrypt_dense_cipher = self._comm.recv(self._name + '_encrypt_dense_cipher', tf.string)
        encrypt_dense_cipher.set_shape(inputs.get_shape())
        encrypt_dense_exponent = self._comm.recv(self._name + '_encrypt_dense_exponent', tf.float32)
        encrypt_dense_exponent.set_shape(inputs.get_shape())
      dense_paillier = paillier.set_ciphertext(encrypt_dense_cipher, encrypt_dense_exponent)
      output = dense_paillier.decrypt(self._encrypt.privacy_key)
      output = output + self._forward_noise
      send_forward = self._comm.send(self._name + "_activate_dense", output)

      def grad(dy):
        send_encrypt_cipher = self._comm.send(self._name + "_grad_encrypt_cipher", paillier.ciphertext)
        send_encrypt_exponent = self._comm.send(self._name + "_grad_encrypt_exponent", paillier.exponent)
        with tf.control_dependencies([send_encrypt_cipher, send_encrypt_exponent]):
          weight_grad_cipher = self._comm.recv(self._name + "_active_weight_grad_cipher", tf.string)
          weight_grad_cipher.set_shape(inputs.get_shape())
          weight_grad_exponent = self._comm.recv(self._name + "_active_weight_grad_exponent", tf.float32)
          weight_grad_exponent.set_shape(inputs.get_shape())
        weight_grad_paillier = PaillierTensor(self._encrypt.public_key)
        weight_grad_paillier = weight_grad_paillier.set_ciphertext(weight_grad_cipher, weight_grad_exponent)
        decrypt_weight_grad = weight_grad_paillier.decrypt(self._encrypt.privacy_key)
        acc_noise_paillier = PaillierTensor(self._encrypt.public_key)
        with tf.control_dependencies([weight_grad_cipher, weight_grad_exponent]):
          acc_noise = tf.tile(self._forward_noise, [tf.shape(inputs)[0], 1])
        acc_noise_paillier = acc_noise_paillier.encrypt(acc_noise)
        send_acc_noise_cipher = self._comm.send(self._name + "_acc_noise_cipher", acc_noise_paillier.ciphertext)
        send_acc_noise_exponent = self._comm.send(self._name + "_acc_noise_exponent", acc_noise_paillier.exponent)
        if self._update_noise:
          noise = tf.random.uniform([1, self._dim], minval=-2**10, maxval=2**10)
        else:
          noise = tf.zeros([1, self._dim], dtype=tf.float32)
        apply_noise = self._apply_forward_noise(noise)
        noise = tf.tile(noise, [tf.shape(inputs)[0], 1])
        decrypt_weight_grad = decrypt_weight_grad + noise / self._learning_rate
        send_weight_grad = self._comm.send(self._name + '_activate_weight_grad', decrypt_weight_grad)
        with tf.control_dependencies([send_acc_noise_cipher, send_acc_noise_exponent, send_weight_grad]):
          grad_cipher = self._comm.recv(self._name + "_active_grad_cipher", tf.string)
          grad_cipher.set_shape(inputs.get_shape())
          grad_exponent = self._comm.recv(self._name + "_active_grad_exponent", tf.float32)
          grad_exponent.set_shape(inputs.get_shape())
        grad_paillier = PaillierTensor(self._encrypt.public_key)
        grad_paillier = grad_paillier.set_ciphertext(grad_cipher, grad_exponent)
        grad_decrypt = grad_paillier.decrypt(self._encrypt.privacy_key)
        with tf.control_dependencies([grad_decrypt]):
          with tf.control_dependencies([apply_noise]):
            return grad_decrypt + dy

      with tf.control_dependencies([send_forward]):
        return tf.identity(inputs), grad
    return tf_compute(inputs)

  def __call__(self, inputs):
    return self.compute(inputs)

  def _apply_forward_noise(self, noise):
    return tf.assign_add(self._forward_noise, noise)


@exporter.export("privacy.EncryptPassiveLayer")
class EncryptPassiveLayer():
  def __init__(self, communicator, dim, recv_dim, public_file, learning_rate=0.01, initializer=None, name='hetero'):
    self._comm = communicator
    self._dim = dim
    self._recv_dim = recv_dim
    self._name = name
    self._learning_rate = learning_rate
    if initializer is None:
      initializer = tf.ones_initializer()
    self._passive_weight = tf.get_variable(self._name + "_passive_weight", [dim], dtype=tf.float32, initializer=initializer, trainable=False)
    self._active_weight = tf.get_variable(self._name + "_active_weight", [dim], dtype=tf.float32, initializer=initializer, trainable=False)
    self._encrypt = PaillierEncrypt()
    self._encrypt.load_public_key_from_file(public_file)

  def compute(self, inputs):
    @tf.custom_gradient
    def tf_compute(inputs):
      recv_shape = inputs.get_shape()[:-1].concatenate(self._recv_dim)
      encrypt_cipher = self._comm.recv(self._name + "_encrypt_cipher", tf.string)
      encrypt_cipher.set_shape(recv_shape)
      encrypt_exponent = self._comm.recv(self._name + "_encrypt_exponent", tf.float32)
      encrypt_exponent.set_shape(recv_shape)
      paillier = PaillierTensor(self._encrypt.public_key)
      paillier = paillier.set_ciphertext(encrypt_cipher, encrypt_exponent)
      active_weight = tf.reshape(self._active_weight, [1, -1])
      active_weight = tf.tile(active_weight, [tf.shape(inputs)[0], 1])
      paillier = paillier.mul_scalar(active_weight)
      noise = tf.random.uniform([1, self._dim], minval=-2**10, maxval=2**10)
      noise = tf.tile(noise, [tf.shape(inputs)[0], 1])
      paillier = paillier.add_scalar(noise)
      send_dense_cipher = self._comm.send(self._name + '_encrypt_dense_cipher', paillier.ciphertext)
      send_dense_exponent = self._comm.send(self._name + '_encrypt_dense_exponent', paillier.exponent)
      with tf.control_dependencies([send_dense_cipher, send_dense_exponent]):
        activate_dense = self._comm.recv(self._name + "_activate_dense", tf.float32)
        activate_dense.set_shape(recv_shape)
      passive_dense = inputs * self._passive_weight
      output = tf.concat([passive_dense, activate_dense - noise], axis=-1)

      def grad(dy):
        dys = tf.split(dy, [self._dim, self._recv_dim], axis=-1)
        passive_dy = dys[0]
        active_dy = dys[1]
        encrypt_cipher = self._comm.recv(self._name + "_grad_encrypt_cipher", tf.string)
        encrypt_cipher.set_shape(recv_shape)
        encrypt_exponent = self._comm.recv(self._name + "_grad_encrypt_exponent", tf.float32)
        encrypt_exponent.set_shape(recv_shape)
        passive_weight_grad = tf.reduce_mean(passive_dy * inputs, axis=0)
        grad_paillier = PaillierTensor(self._encrypt.public_key)
        grad_paillier = grad_paillier.set_ciphertext(encrypt_cipher, encrypt_exponent)
        grad_paillier = grad_paillier.mul_scalar(active_dy)
        grad_paillier = grad_paillier.add_scalar(noise)
        send_grad_cipher = self._comm.send(self._name + "_active_weight_grad_cipher", grad_paillier.ciphertext)
        send_grad_exponent = self._comm.send(self._name + "_active_weight_grad_exponent", grad_paillier.exponent)
        with tf.control_dependencies([send_grad_cipher, send_grad_exponent]):
          activate_weight_grad = self._comm.recv(self._name + "_activate_weight_grad", tf.float32)
          activate_weight_grad.set_shape(recv_shape)
          acc_noise_cipher = self._comm.recv(self._name + "_acc_noise_cipher", tf.string)
          acc_noise_cipher.set_shape(recv_shape)
          acc_noise_exponent = self._comm.recv(self._name + "_acc_noise_exponent", tf.float32)
          acc_noise_exponent.set_shape(recv_shape)
        active_weight_grad = tf.reduce_mean(activate_weight_grad - noise, axis=0)
        # calculate active gradient
        noise_paillier = PaillierTensor(self._encrypt.public_key)
        noise_paillier.set_ciphertext(acc_noise_cipher, acc_noise_exponent)
        active_weight = tf.reshape(self._active_weight, [1, -1])
        active_weight = tf.tile(active_weight, [tf.shape(inputs)[0], 1])
        noise_paillier = noise_paillier.add_scalar(active_weight)
        active_grad_paillier = noise_paillier.mul_scalar(active_dy)

        send_active_grad_cipher = self._comm.send(self._name + "_active_grad_cipher", active_grad_paillier.ciphertext)
        send_active_grad_exponent = self._comm.send(self._name + "_active_grad_exponent", active_grad_paillier.exponent)
        apply_activate = self._apply_active_gradient(active_weight_grad)
        apply_passive = self._apply_passive_gradient(passive_weight_grad)
        with tf.control_dependencies([active_weight_grad, passive_weight_grad, send_active_grad_cipher, send_active_grad_exponent]):
          with tf.control_dependencies([apply_activate, apply_passive]):
            return passive_dy * self._passive_weight

      return output, grad
    return tf_compute(inputs)

  def __call__(self, inputs):
    return self.compute(inputs)

  def _apply_active_gradient(self, active_grad):
    return tf.assign_add(self._active_weight, -self._learning_rate * active_grad)

  def _apply_passive_gradient(self, passive_grad):
    return tf.assign_add(self._passive_weight, -self._learning_rate * passive_grad)
