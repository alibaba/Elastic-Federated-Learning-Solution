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

from tensorflow.python.util import nest

from efl import exporter
from efl.framework import task_scope
from efl.framework.common_define import *

class HookManager(object):
  r'''Manage multigroup hooks and temporary hooks'''
  def __init__(self):
    self._hooks = {}
    self._running_tmp_hooks = []
    self._tmp_hooks = set([])
    self._tf_sess = None
    self._coord = None
    self._sess_cb = None
    self._end_hooks = set([])

  def set_sess_and_coord(self, sess, coord):
    self._tf_sess = sess
    self._coord = coord
    if self._sess_cb:
      self._sess_cb(sess)

  def add_sess_callback(self, cb):
    self._sess_cb = cb

  def add_hooks(self, hooks, mode, task):
    ts = task_scope.TaskScope(mode, task)
    if ts not in self._hooks:
      self._hooks[ts] = []
    self._hooks[ts].extend(hooks)

  def hook_end(self, hook):
    if hook not in self._end_hooks:
      self._end_hooks.add(hook)

  def get_running_hooks(self, mode=None, task=None):
    ts = task_scope.current_task_scope()
    if mode:
      ts._mode = mode
    if task:
      ts._task = task
    hooks = []
    if ts in self._hooks:
      return self._hooks[ts] + self._running_tmp_hooks
    else:
      return self._running_tmp_hooks

  @property
  def all_hooks(self):
    return nest.flatten(self._hooks)

  @property
  def all_tmp_hooks(self) :
    return list(self._tmp_hooks)

  @property
  def tf_sess(self):
    return self._tf_sess

  @property
  def tf_coord(self):
    return self._coord

  @contextlib.contextmanager
  def with_tmp_hooks(self, hooks):
    if self._tf_sess is None or self._coord is None:
      raise RuntimeError('session and coordinator not set')
    for hook in hooks:
      if hook not in self._tmp_hooks:
        self._tmp_hooks.add(hook)
        hook.begin()
        hook.after_create_session(self._tf_sess, self._coord)
    old_hooks = self._running_tmp_hooks
    self._running_tmp_hooks = old_hooks + hooks
    try:
      yield
    finally:
      self._running_tmp_hooks = old_hooks

  def call_hook_begin(self):
    for hook in self.all_hooks:
      hook.end(self._tf_sess)      

  def call_hook_end(self):
    for hook in self.all_hooks:
      if hook not in self._end_hooks:
        hook.end(self._tf_sess)      
    for hook in self.all_tmp_hooks:
      if hook not in self._end_hooks:
        hook.end(self._tf_sess)

_HOOKMGR_INST = HookManager()

def get_hook_manager():
  global _HOOKMGR_INST
  return _HOOKMGR_INST

@exporter.export("with_tmp_hooks")
def with_tmp_hooks(hooks):
  return get_hook_manager().with_tmp_hooks(hooks)
