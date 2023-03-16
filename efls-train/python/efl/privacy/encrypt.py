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

import json

from efl import exporter
from efl.privacy import gmpy_math

class PaillierKeypair(object):
  @staticmethod
  def generate_keypair(n_length=1024, public_file=None, private_file=None):
    p = q = n = None
    n_len = 0

    while n_len != n_length:
      p = gmpy_math.getprimeover(n_length // 2)
      q = p
      while q == p:
        q = gmpy_math.getprimeover(n_length // 2)
      n = p * q
      n_len = n.bit_length()

    public_key = PaillierPublicKey(n)
    private_key = PaillierPrivateKey(public_key, p, q)
    if public_file:
      public_config = {'n': n}
      with open(public_file, 'w') as f:
        json.dump(public_config, f)
    if private_file:
      private_config = {'p': p, 'q': q}
      with open(private_file, 'w') as f:
        json.dump(private_config, f)
    return public_key, private_key

  @staticmethod
  def init_public_key_from_file(file_name):
    with open(file_name) as f:
      public_key = json.load(f)
    return PaillierPublicKey(public_key['n'])

  @staticmethod
  def init_private_key_from_file(public_key, file_name):
    with open(file_name) as f:
      private_key = json.load(f)
    return PaillierPrivateKey(public_key, private_key['p'], private_key['q'])

  @staticmethod
  def init_keypair_from_file(public_file, private_file):
    public_key = PaillierKeypair.init_public_key_from_file(public_file)
    private_key = PaillierKeypair.init_private_key_from_file(public_key, private_file)
    return public_key, private_key


class PaillierPublicKey(object):
  def __init__(self, n):
    self.g = n + 1
    self.n = n
    self.nsquare = n * n
    self.max_int = n // 3 - 1


class PaillierPrivateKey(object):
  def __init__(self, public_key, p, q):
    if not p * q == public_key.n:
      raise ValueError("given public key does not match the given p and q")
    if p == q:
      raise ValueError("p and q have to be different")
    self.public_key = public_key
    if q < p:
      self.p = q
      self.q = p
    else:
      self.p = p
      self.q = q
    self.psquare = self.p * self.p
    self.qsquare = self.q * self.q
    self.q_inverse = gmpy_math.invert(self.q, self.p)
    self.hp = self.h_func(self.p, self.psquare)
    self.hq = self.h_func(self.q, self.qsquare)

  def h_func(self, x, xsquare):
    return gmpy_math.invert(
            self.l_func(gmpy_math.powmod(self.public_key.g,
                                         x - 1, xsquare), x), x)

  def l_func(self, x, p):
    return (x - 1) // p


class Encrypt(object):
  def __init__(self):
    self.public_key = None
    self.privacy_key = None

  def generate_key(self, n_length=0):
    pass

  def set_public_key(self, public_key):
    pass

  def get_public_key(self):
    pass

  def set_privacy_key(self, privacy_key):
    pass

  def get_privacy_key(self):
    pass

  def encrypt(self, value):
    pass

  def decrypt(self, value):
    pass


class PaillierEncrypt(Encrypt):
  def __init__(self):
    super(PaillierEncrypt, self).__init__()

  def generate_key(self, n_length=1024, public_file=None, private_file=None):
    self.public_key, self.privacy_key = PaillierKeypair.generate_keypair(
        n_length=n_length,
        public_file=public_file,
        private_file=private_file)

  def load_key_from_file(self, public_file, private_file):
    self.public_key, self.privacy_key = PaillierKeypair.init_keypair_from_file(public_file, private_file)

  def load_public_key_from_file(self, public_file):
    self.public_key = PaillierKeypair.init_public_key_from_file(public_file)

  def get_key_pair(self):
    return self.public_key, self.privacy_key

  def set_public_key(self, public_key):
    self.public_key = public_key

  def get_public_key(self):
    return self.public_key

  def set_privacy_key(self, privacy_key):
    self.privacy_key = privacy_key

  def get_privacy_key(self):
    return self.privacy_key

@exporter.export("privacy.generate_paillier_key")
def generate_paillier_key(public_file, private_file, n_length=1024):
  encrypt = PaillierEncrypt()
  encrypt.generate_key(n_length=n_length, public_file=public_file, private_file=private_file)
