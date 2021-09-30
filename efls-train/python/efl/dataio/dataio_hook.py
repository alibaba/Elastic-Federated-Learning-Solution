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

import os

import tensorflow as tf
from tensorflow.python.framework import constant_op
from tensorflow.python.data.ops import dataset_ops
from tensorflow.python.ops import control_flow_ops
from tensorflow.python.ops import gen_control_flow_ops
from tensorflow.python.framework import ops
from tensorflow.python.ops import gen_math_ops
from tensorflow.python.ops import math_ops
from tensorflow.python.ops import variables
from tensorflow.python.training import session_run_hook
from tensorflow.python.ops import logging_ops

from efl import exporter
from efl.lib import ops as fed_ops

@exporter.export("data.DataIOHook")
class DataIOHook(session_run_hook.SessionRunHook):

  def __init__(self,
               dataio,
               task_index=0,
               task_num=1,
               save_interval=100,
               name='dataio'):
    self._dataio = dataio
    self._save_interval = save_interval
    if save_interval is not None:
      with ops.device('/cpu:0'):
        empty_state = constant_op.constant("")
        with ops.name_scope(name):
          self._state_variable = [
              variables.VariableV1(
                empty_state,
                trainable=False,
                collections=None,
                name='io_state_{}'.format(i)) for i in range(task_num)
          ]
        remote_state = self._state_variable[task_index]
        self._should_init = gen_math_ops.equal(remote_state, empty_state)
        restore_state = dataio.restore_from_reader_state_op(remote_state)
        self._restore_state = control_flow_ops.group(
            restore_state, logging_ops.print_v2("Restore io from checkpoint."))
        self._local_state = fed_ops.serialize_iterator_to_string(
            dataio._iterator._iterator_resource)
        self._save_state = remote_state.assign(self._local_state)
    else:
      self._should_init = constant_op.constant(True)
      self._restore_state = gen_control_flow_ops.no_op()
      self._save_state = gen_control_flow_ops.no_op()

  def after_create_session(self, sess, coord):
    if sess.run(self._should_init):
      self._dataio.initialize_iter(sess)
    else:
      self._dataio.initialize_iter(sess)
      sess.run(self._restore_state)
    self._step = 0

  def before_run(self, run_context):
    if self._save_interval and self._step % self._save_interval == 0:
      return session_run_hook.SessionRunArgs(self._save_state)
    else:
      return None

  def after_run(self, run_context, run_values):
    self._step += 1

@exporter.export("data.FederalDataIOHook")
class FederalDataIOHook(session_run_hook.SessionRunHook):

  def __init__(self,
               dataio,
               communicator,
               role,
               task_index=0,
               task_num=1,
               save_interval=100,
               name='dataio'):
    self._dataio = dataio
    self._save_interval = save_interval
    self._role = role
    self._communicator = communicator

    if save_interval is not None:
      if role == "leader":
        with ops.device('/cpu:0'):
          empty_state = constant_op.constant("")
          with ops.name_scope(name):
            self._state_variable = [
                variables.VariableV1(
                  empty_state,
                  trainable=False,
                  collections=None,
                  name='io_state_{}'.format(i)) for i in range(task_num)
            ]
          remote_state = self._state_variable[task_index]
          self._should_init = gen_math_ops.equal(remote_state, empty_state)
          self._restore_state = dataio.restore_from_reader_state_op(remote_state)
          self._local_state = fed_ops.serialize_iterator_to_string(
              dataio._iterator._iterator_resource)
          remote_sample_index = fed_ops.get_sample_index_from_iter_string(self._local_state)
          remote_block_id = fed_ops.get_block_id_from_iter_string(self._local_state)
          send_state = self._communicator.send_reader_state(name, remote_block_id, remote_sample_index)
          self._send_state = control_flow_ops.group(
              send_state,
              logging_ops.print_v2("Restore io from checkpoint, and send state to follower."))
          self._save_state = remote_state.assign(self._local_state)
      elif role == "follower":
        self._should_init = constant_op.constant(True)
        self._restore_state = gen_control_flow_ops.no_op()
        self._save_state = gen_control_flow_ops.no_op()
      else:
        raise ValueError("Role must be one of `leader` or `follower`.")
    else:
      self._should_init = constant_op.constant(True)
      self._restore_state = gen_control_flow_ops.no_op()
      self._save_state = gen_control_flow_ops.no_op()

  def after_create_session(self, sess, coord):
    if self._role == 'leader':
      self._should_init_flag = sess.run(self._should_init)
      if self._should_init_flag:
        self._dataio.initialize_iter(sess)
      else:
        self._dataio.initialize_iter(sess)
        sess.run(self._restore_state)
    else:
      self._dataio.initialize_iter(sess)
    self._step = 0

  def before_run(self, run_context):
    if self._step == 0 and self._role == 'leader' and not self._should_init_flag:
      run_context.session.run(self._send_state)
    if self._save_interval and self._step % self._save_interval == 0 and self._role == 'leader':
      return session_run_hook.SessionRunArgs(self._save_state)
    else:
      return None

  def after_run(self, run_context, run_values):
    self._step += 1

  def end(self, sess):
    pass
