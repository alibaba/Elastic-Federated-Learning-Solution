# Copyright 2021 Alibaba Group Holding Limited. All Rights Reserved.
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

import hashlib
import random

import rsa
from cityhash import CityHash64 as OneWayHash
from gmpy2 import powmod, divm

import unittest


def bytes2int(byte, byteorder='little'):
  return int.from_bytes(byte, byteorder)

def int2bytes(digit, byte_len, byteorder='little'):
  return int(digit).to_bytes(byte_len, byteorder)

class Constant(object):
  """
  Constant variables
  """
  RSA_PUBLIC_KEY_FILENAME = "test_rsa.pub"
  RSA_PRIVATE_KEY_FILENAME = "test_rsa"


class RsaSigner(object):
  """
  RSA signer base
  """
  def __init__(self):
    pass

  @staticmethod
  def load_key(key_filepath, is_public):
    with open(key_filepath, 'rb') as fd:
      if is_public:
        return rsa.PublicKey.load_pkcs1(fd.read())
      else:
        return rsa.PrivateKey.load_pkcs1(fd.read())

  @staticmethod
  def generate_rsa_keys(public_key_path, private_key_path, key_length=2048):
    pub_key, prv_key = rsa.newkeys(key_length)
    # save public key
    with open(public_key_path, 'wb') as fd:
      fd.write(pub_key.save_pkcs1())
    # save private key
    with open(private_key_path, 'wb') as fd:
      fd.write(prv_key.save_pkcs1())

  @staticmethod
  def fdh(value):
    return hashlib.sha256(bytes(str(value), encoding='utf-8')).hexdigest()

  @staticmethod
  def fdh_list(ids, ret_int=False):
    if ret_int:
      return [int(RsaSigner.fdh(item), 16) for item in ids]
    return [RsaSigner.fdh(item) for item in ids]

  @staticmethod
  def oneway_hash_list(ids):
    return [hex(OneWayHash(str(item)))[2:] for item in ids]

  @staticmethod
  def rsa_sign_list(ids, d, n):
    return [int(powmod(x, d, n).digits()) for x in ids]


class LeaderRsaSigner(RsaSigner):
  """
  Leader signer
  """
  def __init__(self, rsa_public_key_filepath, rsa_private_key_filepath):
    self.rsa_public_key_ = RsaSigner.load_key(rsa_public_key_filepath, True)
    self.rsa_private_key_ = RsaSigner.load_key(rsa_private_key_filepath, False)

  def sign_func(self, ids):
    # step1. hash ids
    hashed_ids = RsaSigner.fdh_list(ids, True)
    # step2. signed hash ids with private key
    signed_hashed_ids = RsaSigner.rsa_sign_list(hashed_ids, self.rsa_private_key_.d, self.rsa_private_key_.n)
    # step3. second hash
    hashed_signed_hashed_ids = RsaSigner.oneway_hash_list(signed_hashed_ids)
    return hashed_signed_hashed_ids

  def sign_blinded_ids_from_follower(self, ids):
    d, n = self.rsa_private_key_.d, self.rsa_private_key_.n
    byte_len = n.bit_length() // 8
    return [int2bytes(powmod(bytes2int(item), d, n).digits(), byte_len) for item in ids]


class FollowerRsaSigner(RsaSigner):
  """
  follower signer
  """
  def __init__(self, rsa_public_key_filepath):
    self.rsa_public_key_ = RsaSigner.load_key(rsa_public_key_filepath, True)

  def sign_func(self, ids, leader_signer):
    # step1. hash ids
    hashed_ids = RsaSigner.fdh_list(ids, True)
    # step2. blind hash ids
    blinded_hashed_ids, blind_numbers = self.blind_ids(hashed_ids)
    # step3. leader sign blind ids
    signed_blinded_hashed_ids = leader_signer.sign_blinded_ids_from_follower(blinded_hashed_ids)
    # step4. deblind signed ids
    return self.deblind_signed_ids(signed_blinded_hashed_ids, blind_numbers)

  def blind_ids(self, ids):
    e, n = self.rsa_public_key_.e, self.rsa_public_key_.n
    blind_numbers = [random.SystemRandom().getrandbits(256) for i in range(len(ids))]
    byte_len = n.bit_length() // 8
    blinded_hashed_ids = [int2bytes((powmod(powmod(r, e, n) * x, 1, n)).digits(), byte_len) for x, r in zip(ids, blind_numbers)]
    return blinded_hashed_ids, blind_numbers

  def deblind_signed_ids(self, signed_blinded_hashed_ids, blind_numbers):
    n = self.rsa_public_key_.n
    signed_blinded_hashed_ids = [bytes2int(item) for item in signed_blinded_hashed_ids]
    signed_hashed_ids = [int(divm(x, r, n).digits()) for x, r in zip(signed_blinded_hashed_ids, blind_numbers)]
    hashed_signed_hashed_ids = RsaSigner.oneway_hash_list(signed_hashed_ids)
    return hashed_signed_hashed_ids

class TestRsaPsi(unittest.TestCase):
  def setUp(self):
    # step1. generate rsa keys
    RsaSigner.generate_rsa_keys(Constant.RSA_PUBLIC_KEY_FILENAME, Constant.RSA_PRIVATE_KEY_FILENAME)

  def test_psi(self):
    inputs = [1, 2, 3, 4, 5, 6.5, '7']
    # step2. leader sign
    leader = LeaderRsaSigner(Constant.RSA_PUBLIC_KEY_FILENAME, Constant.RSA_PRIVATE_KEY_FILENAME)
    leader_signed_ids = leader.sign_func(inputs)

    # step3. follower sign
    follower = FollowerRsaSigner(Constant.RSA_PUBLIC_KEY_FILENAME)
    follower_signed_ids = follower.sign_func(inputs, leader)

    print(leader_signed_ids)
    print(follower_signed_ids)
    self.assertEqual(leader_signed_ids, follower_signed_ids)

if __name__ == '__main__':
  unittest.main(verbosity=1)
