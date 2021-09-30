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

import types

class ExportManager(object):
  def __init__(self):
    self._dict = {}

  def export(self, key, val):
    if key in self._dict:
      raise ImportError("efl internal filename error")
    self._dict[key] = val

  def filldict(self, g):
    for k, v in self._dict.items():
      s = k.split('.')
      dct = g
      while len(s) > 1:
        if s[0] not in dct:
          dct[s[0]] = types.ModuleType(s[0])
        dct = dct[s[0]].__dict__
        s = s[1:]
      dct[s[0]] = v

_export_manager = ExportManager()

def export(name):
  def _export(item):
    _export_manager.export(name, item)
    return item
  return _export

def filldict(g):
  _export_manager.filldict(g)
