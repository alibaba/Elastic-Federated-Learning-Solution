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

import tensorflow as tf
from tensorflow.python.platform import tf_logging
from tensorflow.python.ops import array_ops
from tensorflow.python.training import session_run_hook
from tensorflow.python.training.training_util import get_or_create_global_step
from tensorflow.python.ops import variables
from tensorflow.python.framework import ops
from tensorflow.python.ops import state_ops

from efl.lib import ops as fed_ops
from efl import exporter

import time

@exporter.export("Communicator")
class Communicator(object):

  def __init__(self, federal_role, peer_addr, local_addr,
               client_thread_num=None, server_thread_num=None,
               scanning_interval_milliseconds=None, default_timeout_milliseconds=None):
    self._handler = fed_ops.communicator_handle_op()
    self._recv_set = set()
    self._dataset_set = set()
    self._local_step = variables.VariableV1(
        array_ops.constant(0, dtype=tf.int64),
        trainable=False,
        collections=[ops.GraphKeys.LOCAL_VARIABLES],
        name='communicator_local_step')
    self._recv_list_ph = array_ops.placeholder(tf.string, shape=[None], name='recv_map_ph')
    self._dataset_list_ph = array_ops.placeholder(tf.string, shape=[None], name='dataset_ph')
    self._create_op = fed_ops.create_communicator(self._handler,
                                                  self._recv_list_ph,
                                                  self._dataset_list_ph,
                                                  local_addr,
                                                  peer_addr,
                                                  scanning_interval_milliseconds,
                                                  default_timeout_milliseconds)
    if federal_role not in ('leader', 'follower'):
      raise ValueError("federal_role must be set one of [leader/follower] in Communicator")
    self._federal_role = federal_role
    if federal_role == 'leader':
      self._connect_op = fed_ops.response_connection(self._handler,
                                                     client_thread_num,
                                                     server_thread_num)
    else:
      self._connect_op = fed_ops.request_connection(self._handler,
                                                    client_thread_num,
                                                    server_thread_num)
    self._end_op = fed_ops.close_connection(self._handler)
    self._version_ph = array_ops.placeholder(tf.string, shape=[], name='ckpt_version_ph')
    self._send_ckpt_op = fed_ops.send_ckpt_version(self._handler, self._version_ph)
    self._recv_ckpt_op = fed_ops.recv_ckpt_version(self._handler)
    self._add_local_step = state_ops.assign_add(self._local_step, 1)

  def send(self, name, tensor):
    return fed_ops.send_tensor(self._handler, tensor, self._local_step, name)

  def recv(self, name, dtype=tf.float32):
    self._recv_set.add(name)
    return fed_ops.receive_tensor(self._handler, self._local_step, name, dtype)

  def send_ckpt_version(self, sess, version):
    sess.run(self._send_ckpt_op, feed_dict={self._version_ph: version})

  def recv_ckpt_version(self, sess):
    return sess.run(self.recv_ckpt_op)

  def send_reader_state(self, name, block_id, sample_index):
    self._dataset_set.add(name)
    return fed_ops.send_reader_state(self._handler, block_id, sample_index, name)

  def recv_reader_state(self, name):
    return fed_ops.recv_reader_state(self._handler, name)

  def initialize(self, sess):
    sess.run(self._create_op, feed_dict={self._recv_list_ph: list(self._recv_set), self._dataset_list_ph: list(self._dataset_set)})
    if self._federal_role == 'leader':
      sess.run(self._connect_op)
    else:
      while True:
        try:
          sess.run(self._connect_op)
        except tf.errors.UnavailableError as e:
          tf_logging.info("Connecting failed with leader, wait 10 second.")
          time.sleep(10)
        else:
          break

  def shutdown(self, sess):
    sess.run(self._end_op)

  def terminate_reader(self, name):
    return fed_ops.terminate_reader(self._handler, name)

  @property
  def hook(self):
    if not hasattr(self, '_hook'):
      self._hook = CommunicatorHook(self)
    return self._hook

  def add_step(self):
    return self._add_local_step


class CommunicatorHook(session_run_hook.SessionRunHook):

  def __init__(self, communicator):
    self._communicator = communicator

  def after_create_session(self, sess, coord):
    self._communicator.initialize(sess)

  def before_run(self, run_context):
    return None

  def after_run(self, run_context, run_values):
    run_context.session.run(self._communicator.add_step())

  def end(self, sess):
    self._communicator.shutdown(sess)
