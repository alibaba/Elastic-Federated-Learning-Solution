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

from xfl.service.data_join_client import DataJoinClient


def bytes2int(byte, byteorder='little'):
  return int.from_bytes(byte, byteorder)

def int2bytes(digit, byte_len, byteorder='little'):
  return int(digit).to_bytes(byte_len, byteorder)

class RsaSigner(object):
  """
  RSA signer base
  """
  def __init__(self):
    pass

  @staticmethod
  def load_key(key_bytes, is_public):
      if is_public:
        return rsa.PublicKey.load_pkcs1(key_bytes)
      else:
        return rsa.PrivateKey.load_pkcs1(key_bytes)

  @staticmethod
  def generate_rsa_keys(key_length=2048):
    pub_key, prv_key = rsa.newkeys(key_length)
    return pub_key.save_pkcs1(), prv_key.save_pkcs1()

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
    return [hex(OneWayHash(str(item)))[2:].encode('utf-8') for item in ids]

  @staticmethod
  def rsa_sign_list(ids, d, n):
    return [int(powmod(x, d, n).digits()) for x in ids]



class ServerRsaSigner(RsaSigner):
  def __init__(self, rsa_public_key_bytes: str = None, rsa_private_key_bytes: str = None, ):
    '''
      When keys are not specified, RsaSignner will generate a pair of keys everytime.
    '''
    if rsa_public_key_bytes is None or rsa_private_key_bytes is None:
      self.pub_key_bytes_, self.prv_key_bytes_ = self.generate_rsa_keys()
    else:
      self.pub_key_bytes_, self.prv_key_bytes_ = rsa_public_key_bytes, rsa_private_key_bytes
    self.rsa_public_key_ = RsaSigner.load_key(self.pub_key_bytes_, True)
    self.rsa_private_key_ = RsaSigner.load_key(self.prv_key_bytes_, False)

  def sign_func(self, ids):
    hashed_ids = RsaSigner.fdh_list(ids, True)
    signed_hashed_ids = RsaSigner.rsa_sign_list(hashed_ids, self.rsa_private_key_.d, self.rsa_private_key_.n)
    hashed_signed_hashed_ids = RsaSigner.oneway_hash_list(signed_hashed_ids)
    return hashed_signed_hashed_ids

  def sign_blinded_ids_from_client(self, ids):
    d, n = self.rsa_private_key_.d, self.rsa_private_key_.n
    byte_len = n.bit_length() // 8
    return [int2bytes(powmod(bytes2int(item), d, n).digits(), byte_len) for item in ids]

  def get_public_key_bytes(self):
    return self.pub_key_bytes_

class ClientRsaSigner(RsaSigner):
  def __init__(self, rsa_public_key_bytes):
    self.rsa_public_key_ = RsaSigner.load_key(rsa_public_key_bytes, True)

  def sign_func(self, ids, data_join_cli: DataJoinClient, bucket_id):
    hashed_ids = RsaSigner.fdh_list(ids, True)
    blinded_hashed_ids, blind_numbers = self._blind_ids(hashed_ids)
    signed_blinded_hashed_ids = data_join_cli.sign_blinded_ids_from_server(blinded_hashed_ids, bucket_id)
    return self._deblind_signed_ids(signed_blinded_hashed_ids, blind_numbers)

  def _blind_ids(self, ids):
    e, n = self.rsa_public_key_.e, self.rsa_public_key_.n
    blind_numbers = [random.SystemRandom().getrandbits(256) for _ in range(len(ids))]
    byte_len = n.bit_length() // 8
    blinded_hashed_ids = [int2bytes((powmod(powmod(r, e, n) * x, 1, n)).digits(), byte_len) for x, r in zip(ids, blind_numbers)]
    return blinded_hashed_ids, blind_numbers

  def _deblind_signed_ids(self, signed_blinded_hashed_ids, blind_numbers):
    n = self.rsa_public_key_.n
    signed_blinded_hashed_ids = [bytes2int(item) for item in signed_blinded_hashed_ids]
    signed_hashed_ids = [int(divm(x, r, n).digits()) for x, r in zip(signed_blinded_hashed_ids, blind_numbers)]
    hashed_signed_hashed_ids = RsaSigner.oneway_hash_list(signed_hashed_ids)
    return hashed_signed_hashed_ids
