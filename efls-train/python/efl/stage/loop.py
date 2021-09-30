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

import sys
import time

import tensorflow.compat.v1 as tf
from tensorflow.python.framework import errors
from tensorflow.python.training import training_util
from tensorflow.python.training.sync_replicas_optimizer import _SyncReplicasOptimizerHook

from efl import exporter
from efl.framework import stage
from efl.framework import hook_manager

@exporter.export("stage.LoopStage")
class LoopStage(stage.Stage):
  def __init__(self, run_ops, is_training=True, step=None, time=None):
    self._is_training = is_training
    self._step = step
    self._time = time
    self._finish = False
    if is_training:
      self._run_ops = run_ops + tf.get_collection(tf.GraphKeys.UPDATE_OPS)
    else:
      self._run_ops = run_ops
    self._lstep = 0

  @property
  def finish(self):
    return self._finish

  def run(self, feed_dict={}):
    start_step = self._lstep
    start_time = int(time.time())
    try :
      while True:
        if self.sess.should_stop():
          tf.logging.info("sess.should_stop is True, LoopStage finish")
          self._finish = True
          break
        self.sess.run(self._run_ops, feed_dict = feed_dict)
        self._lstep += 1
        if self._step and (self._lstep - start_step) >= self._step:
          tf.logging.info("run [%s] steps, LoopStage finish", self._lstep)
          break
        run_time = int(time.time() - start_time)
        if self._time and run_time > self._time:
          tf.logging.info("run [%s] seconds, LoopStage finish", run_time)
          break
    except (errors.OutOfRangeError, StopIteration):
      tf.logging.info("catch OutOfRangeError or StopIteration, LoopStage finish")
      self._finish = True
      self._deal_with_sync_optimize_hook()

  def _deal_with_sync_optimize_hook(self):
    for h in hook_manager.get_hook_manager().get_running_hooks():
      if isinstance(h, _SyncReplicasOptimizerHook):
        h.end(self.sess._tf_sess())
        hook_manager.get_hook_manager().hook_end(h)
