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

import copy
import contextlib

from efl import exporter
from efl.framework.common_define import MODE

class TaskScope(object):
  def __init__(self, mode=None, task=None):
    self._mode = mode
    self._task = task

  @property
  def mode(self):
    return self._mode

  @property
  def task(self):
    return self._task

  def __str__(self):
    return "{}_{}".format(self.mode, self.task)

  def __hash__(self):
    return hash(self.__str__())

  def __eq__(self, other):
    return (self.mode, self.task) == (other.mode, other.task)

  def __lt__(self, other):
    return (self.mode.value, str(self.task)) < (other.mode.value, str(other.task))

_CURRENT_TASK_SCOPE = TaskScope()
@exporter.export("task_scope")
@contextlib.contextmanager
def task_scope(mode=None, task=None):
  global _CURRENT_TASK_SCOPE
  old_scope = _CURRENT_TASK_SCOPE
  _CURRENT_TASK_SCOPE = TaskScope(mode, task)
  try:
    yield
  finally:
    _CURRENT_TASK_SCOPE = old_scope

@exporter.export("current_task_scope")
def current_task_scope():
  global _CURRENT_TASK_SCOPE
  return copy.deepcopy(_CURRENT_TASK_SCOPE)
