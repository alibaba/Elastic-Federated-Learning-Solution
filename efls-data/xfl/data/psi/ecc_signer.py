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


import os
from hashlib import sha256
from curve25519 import _curve25519


def _hash_value(value):
    return sha256(b"curve25519"+value).digest()

class EccSigner(object):
    def __init__(self, secret=None, hashfunc=None):
        if secret is not None:
            if not isinstance(secret, bytes) or len(secret) != 32:
                raise TypeError("secret must be 32-byte string")
            self._private = _curve25519.make_private(secret)
        else:
            self._private = _curve25519.make_private(os.urandom(32))

        if hashfunc is None:
            self._hashfunc = _hash_value
        else:
            self._hashfunc = hashfunc
            #check hash func
            t = self._hashfunc(b'test')
            if not isinstance(t, bytes) or len(t) != 32:
                raise TypeError("the return value of hashfunc  must be 32 bytes!")

    '''
    sign random baytes array, return 32-bytes
    '''
    def sign_hash(self, value):
        #assert isinstance(value , bytes)
        return _curve25519.make_shared(self._private, self._hashfunc(value))

    '''
    sign 32-bytes array, return 32-bytes
    '''
    def sign(self, value):
        #if not isinstance(value, bytes) or len(value) != 32:
        #    raise TypeError("secret must be 32-byte string")
        return _curve25519.make_shared(self._private, value)
