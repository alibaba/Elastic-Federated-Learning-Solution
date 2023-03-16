import sys
sys.path.insert(0, '.')

import os
import shutil
import numpy as np
import unittest

import tensorflow.compat.v1 as tf

import efl
from efl.privacy.paillier_tensor import PaillierTensor
from efl.privacy.encrypt import PaillierEncrypt

class TestPaillierTensor(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    pass

  @classmethod
  def tearDownClass(cls):
    pass
  
  def test_encrypt_decrypt(self):
    encrypt = PaillierEncrypt()
    encrypt.generate_key()
    paillier = PaillierTensor(encrypt.public_key)
    inputs = tf.constant([-1.0, -1.1, -1.2, 1.3, 1.4, 1.5], dtype=tf.float32)
    inputs = tf.reshape(inputs, [3, 2])
    paillier.encrypt(inputs)
    output = paillier.decrypt(encrypt.privacy_key)
    sess = tf.Session()
    before_encrypt, after_decrypt = sess.run([inputs, output])
    self.assertTrue(np.allclose(before_encrypt, after_decrypt))

  def test_add_scalar(self):
    encrypt = PaillierEncrypt()
    encrypt.generate_key()
    paillier = PaillierTensor(encrypt.public_key)
    inputs = tf.constant([-1.0, -1.1, -1.2, 1.3, 1.4, 1.5], dtype=tf.float32)
    inputs = tf.reshape(inputs, [3, 2])
    paillier.encrypt(inputs)
    paillier = paillier.add_scalar([[-1., 2.], [-0.5, 0.2], [10., 200.2]])
    output = paillier.decrypt(encrypt.privacy_key)
    sess = tf.Session()
    result = sess.run(output)
    self.assertTrue(np.allclose(result, [[-2., 0.9], [-1.7, 1.5], [11.4, 201.7]]))

  def test_mul_scalar(self):
    encrypt = PaillierEncrypt()
    encrypt.generate_key()
    paillier = PaillierTensor(encrypt.public_key)
    inputs = tf.constant([-1.0, -1.1, -1.2, 1.3, 1.4, 1.5], dtype=tf.float32)
    inputs = tf.reshape(inputs, [3, 2])
    paillier.encrypt(inputs)
    paillier = paillier.mul_scalar([[-1., 2.], [-0.5, 0.2], [-10., 200.2]])
    output = paillier.decrypt(encrypt.privacy_key)
    sess = tf.Session()
    result = sess.run(output)
    self.assertTrue(np.allclose(result, [[1., -2.2], [0.6, 0.26], [-14,  300.3]]))

if __name__ == '__main__':  
    unittest.main()
