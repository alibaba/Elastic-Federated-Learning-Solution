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

import unittest
import os
from xfl.data.psi.ecc_signer import EccSigner
from binascii import hexlify

def user_hash_func(value):
    return b'a'*32

def user_error_hash_func(value):
    return None

class TestEccSigner(unittest.TestCase):
    def test_ecc_signer(self):
        private_key = os.urandom(32)
        v = [b'aaa', b'bbb', b'ccc']
        signer1 = EccSigner()
        signer2 = EccSigner()
        for i in v:
            self.assertEqual(signer2.sign(signer1.sign_hash(i)),
                    signer1.sign(signer2.sign_hash(i)))
        for i in v:
            self.assertNotEqual(signer1.sign_hash(i), signer2.sign_hash(i))

        #test user set private_key
        s1 = EccSigner(private_key)
        s2 = EccSigner(private_key)
        for i in v:
            self.assertEqual(s1.sign_hash(i), s2.sign_hash(i))

        #test user defined hash func
        pk=b'p'*32
        target_v = b'8bb21ae817643480a77910370fab9d8d0fccf8ec05bb9412531adb3983348104'
        sh1 = EccSigner(secret=pk, hashfunc=user_hash_func)
        [self.assertEqual((hexlify(sh1.sign_hash(i))), target_v) for i in v]

        #test illegal udf
        with self.assertRaises(TypeError):
            sh2 = EccSigner(hashfunc=user_error_hash_func)

if __name__ == '__main__':
  unittest.main(verbosity=1)
