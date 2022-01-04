import sys
sys.path.insert(0, '.')

import unittest
import numpy as np
import tensorflow.compat.v1 as tf
from efl.privacy.paillier import PaillierTensor, PaillierKeypair
from efl.privacy.paillier import fixedpoint_encode, fixedpoint_decode

class TestPaillierTensor(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    pass

  @classmethod
  def tearDownClass(cls):
    pass
 
  def test_encrypt_decrypt_encode_decode(self):
    keypair = PaillierKeypair()
    sess = tf.Session()
    sess.run(keypair.initialize())
    sess.run(keypair.generate_keypair())
    a = tf.random.normal(shape=[100, 100])
    b = fixedpoint_encode(a)
    b.mantissa = keypair.encrypt(b.mantissa)
    b.mantissa = b.mantissa.decrypt()
    b = fixedpoint_decode(b)
    a, b = sess.run([a, b])
    self.assertTrue(np.allclose(a, b))

  def test_add(self):
    keypair = PaillierKeypair()
    sess = tf.Session()
    sess.run(keypair.initialize())
    sess.run(keypair.generate_keypair())
    a = tf.random.normal(shape=[100, 100])
    b = tf.random.normal(shape=[100, 100])
    c1 = a + b
    a = fixedpoint_encode(a)
    a.mantissa = keypair.encrypt(a.mantissa)
    c2 = a + b
    c2.mantissa = c2.mantissa.decrypt()
    c2 = fixedpoint_decode(c2)
    c1, c2 = sess.run([c1, c2])
    self.assertTrue(np.allclose(c1, c2))

  def test_mul_scalar(self):
    keypair = PaillierKeypair()
    sess = tf.Session()
    sess.run(keypair.initialize())
    sess.run(keypair.generate_keypair())
    a = tf.random.normal(shape=[100, 100])
    b = tf.random.normal(shape=[100, 100])
    c1 = a * b
    a = fixedpoint_encode(a)
    a.mantissa = keypair.encrypt(a.mantissa)
    c2 = a * b
    c2.mantissa = c2.mantissa.decrypt()
    c2 = fixedpoint_decode(c2)
    c1, c2 = sess.run([c1, c2])
    self.assertTrue(np.allclose(c1, c2))

  def test_matmul(self):
    keypair = PaillierKeypair()
    sess = tf.Session()
    sess.run(keypair.initialize())
    sess.run(keypair.generate_keypair())
    a = tf.random.normal(shape=[100, 100])
    b = tf.random.normal(shape=[100, 100])
    c1 = a @ b
    a = fixedpoint_encode(a)
    a.mantissa = keypair.encrypt(a.mantissa)
    c2 = a @ b
    c2.mantissa = c2.mantissa.decrypt()
    c2 = fixedpoint_decode(c2)
    c1, c2 = sess.run([c1, c2])
    self.assertTrue(np.allclose(c1, c2, 1e-5, 1e-4))

if __name__ == '__main__':  
    unittest.main()
