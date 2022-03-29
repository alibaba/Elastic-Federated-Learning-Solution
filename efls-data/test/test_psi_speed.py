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
import time
from xfl.data.psi.rsa_signer import ServerRsaSigner
from xfl.data.psi.ecc_signer import EccSigner

class TestRsaPsi(unittest.TestCase):
  def setUp(self):
    self._input_data = []
    self._data_size = 1000
    for i in range(self._data_size):
      self._input_data.append(os.urandom(32))

  def test_psi_speed(self):
    es = EccSigner()
    rs = ServerRsaSigner()

    begin = time.time()
    for d in self._input_data:
      es.sign(es.sign(d))
    end = time.time()
    print ('')
    print('========ecc sign speed result =======')
    print('sign qps: %.2f'%(self._data_size/(end-begin)))
    print('===================================================')

    begin = time.time()
    for d in self._input_data:
      rs.sign_func([d])
    end = time.time()
    print ('')
    print('========rsa sign speed result =======')
    print('sign qps: %.2f'%(self._data_size/(end-begin)))
    print('===================================================')

if __name__ == '__main__':
  unittest.main(verbosity=1)
