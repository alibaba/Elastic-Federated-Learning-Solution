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

import json
import contextlib
import tensorflow.compat.v1 as tf
import time

from tensorflow.python.framework import errors
from tensorflow.core.protobuf import cluster_pb2
from tensorflow.python.training import server_lib

from efl import exporter
from efl.utils import config
from efl.utils import failover_patch

class Context(object):
  def __init__(self, sess_config):
    self._root_scope = tf.get_variable_scope()
    self._sess_config = sess_config

  @property
  def main_device(self):
    raise NotImplementedError()

  @property
  def session_master(self):
    raise NotImplementedError()

  @property
  def session_config(self):
    return self._sess_config

  def scope(self):
    raise NotImplementedError()

class LocalContext(Context):
  def __init__(self, sess_config=None):
    super(LocalContext, self).__init__(sess_config)

  @property
  def main_device(self):
    return "/CPU:0"

  @property
  def session_master(self):
    return ""

  @property
  def session_config(self):
    cfg = super(LocalContext, self).session_config
    return cfg or tf.ConfigProto()

  @contextlib.contextmanager
  def scope(self):
    try:
      with tf.variable_scope(self._root_scope, reuse=tf.AUTO_REUSE):
        yield
    finally:
      pass

class DistributedContext(Context):
  def __init__(self, sess_config=None, protocol='grpc'):
    super(DistributedContext, self).__init__(sess_config)
    self._job = config.get_task_name()
    self._task = config.get_task_index()
    self._protocol = protocol
    self.create_simple_server()
    self.maybe_join()

  def create_simple_server(self):
    cfg = super(DistributedContext, self).session_config
    cfg = cfg or tf.ConfigProto(log_device_placement=False)
    cluster = config.get_cluster()
    cluster_def = cluster_pb2.ClusterDef()
    for role, addrs in cluster.items():
      job_def = cluster_pb2.JobDef()
      job_def.name = role
      for i, addr in enumerate(addrs):
        job_def.tasks[i] = addr
      cluster_def.job.append(job_def)
    self._simple_server = server_lib.Server(
      cluster_def, self._job, self._task,
      protocol=self._protocol, config=cfg)

  @property
  def main_device(self):
    return "/job:scheduler/task:0/CPU:0"

  def maybe_join(self):
    if self._job in ["ps", "scheduler"]:
      self._simple_server.join()

  @property
  def session_master(self):
    return self._simple_server.target

  @property
  def session_config(self):
    return self._simple_server.server_def.default_session_config

  @contextlib.contextmanager
  def scope(self):
    failover_patch.patch()
    try:
      with tf.device(tf.train.replica_device_setter(
          worker_device="/job:worker/task:%d" % config.get_task_index(),
          ps_tasks=config.get_server_num())):
        failover_patch.create_sentinel_variables()
        with tf.variable_scope(
          self._root_scope, partitioner = tf.min_max_variable_partitioner(
            config.get_server_num(), min_slice_size=(128 << 10)),
          reuse=tf.AUTO_REUSE):
          yield
    finally:
      pass

def simple_context(session_config=None,
                   federal_role=None,
                   communicator=None,
                   protocol='grpc'):
  failover_patch.init_federal_env(federal_role, communicator)
  if config.local_mode():
    return LocalContext(session_config)
  else:
    return DistributedContext(session_config, protocol)
