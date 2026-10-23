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
from xfl.data import utils
from xfl.data.utils import get_sample_store_key, split_sample_store_key


class TestUtils(unittest.TestCase):
    def test_gather_res(self):
        ids = [1,2,3,4]
        existence = [True,False,False,True]
        res = utils.gather_res(ids, existence)
        self.assertEqual(res,[1,4])
        ids=[1,2,3,4]
        existence = [False] * len(ids)
        res = utils.gather_res(ids, existence)
        self.assertEqual(res,[])

    def test_sample_store_key_round_trips_delimiters_and_escapes(self):
        self.assertEqual(get_sample_store_key(b"customer", 42), b"customer#42")
        hash_value = b"customer#segment\\#tail"
        sort_value = b"event#time\\slot"
        key = get_sample_store_key(hash_value, sort_value)
        self.assertEqual(split_sample_store_key(key), [hash_value, sort_value])

        first = get_sample_store_key(b"a#", b"b")
        second = get_sample_store_key(b"a", b"#b")
        self.assertNotEqual(first, second)
        self.assertEqual(split_sample_store_key(first), [b"a#", b"b"])

