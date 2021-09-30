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

import mmh3


def check_sum(values: list):
  _check_sum = CheckSum()
  for i in values:
    if isinstance(i, bytes):
      _check_sum.add(i)
    elif isinstance(i, list):
      _check_sum.add_list(i)
    else:
      raise TypeError(type(values))
  return _check_sum.get_check_sum()


class CheckSum(object):
  def __init__(self, seed=0):
    self._cur = seed

  def add(self, value: bytes):
    self._cur = mmh3.hash(str(self._cur).encode('utf-8') + value)

  def add_list(self, value: list):
    for i in value:
      self.add(i)

  def get_check_sum(self):
    return self._cur
