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

import contextlib

_PATCHES = []
def patch(patch, module, name):
  global _PATCHES
  _PATCHES.append((patch, module, name))

@contextlib.contextmanager
def scope():
  global _PATCHES
  old_func = [x[1].__dict__[x[2]] for x in _PATCHES]
  for x in _PATCHES:
    setattr(x[1], x[2], x[0])
  try:
    yield
  finally:
    for i, x in enumerate(_PATCHES):
      setattr(x[1], x[2], old_func[i])

def patch_now(patch, module, name):
  setattr(module, name, patch)
