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

import re

def get_vars_from_scope(vars, scope):
  if scope is None:
    return vars
  else:
    result = []
    regex = re.compile(scope)
    for name, item in vars:
      try:
        if regex.match(item.name):
          result.append((name, item))
      except AttributeError:
        # items with no name are ignored.
        pass
    return result

def get_recv_grad_vars(model, task, scope=None):
  if hasattr(model, 'recv_grad_ops'):
    recv_grad_vars = model.recv_grad_ops[task]
    return get_vars_from_scope(recv_grad_vars, scope)
  else:
    return []
