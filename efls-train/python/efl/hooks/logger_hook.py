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

import tensorflow.compat.v1 as tf
import datetime
import time
from efl import exporter

@exporter.export("hooks.LoggerHook")
class LoggerHook(tf.estimator.SessionRunHook):
  def __init__(self, global_step, every_n_iter, every_n_secs=None,
      counter_increment=1):
    self._global_step = global_step
    self._metrics = []
    self._counter_increment = counter_increment
    self._timer = tf.train.SecondOrStepTimer(
        every_secs=every_n_secs,
        every_steps=every_n_iter)

  def add_metrics(self, name, tensor):
    self._metrics.append((name, tf.convert_to_tensor(tensor)))

  def after_create_session(self, sess, coord):
    self._counter = 0
    self._should_trigger = False
    self._last_gstep = 0
    self._timer.reset()

  def before_run(self, run_context):
    self._should_trigger = self._timer.should_trigger_for_step(self._counter)
    if self._should_trigger:
      return tf.train.SessionRunArgs({
        "result": [i[1] for i in self._metrics],
        "global_step": self._global_step})
    else:
      self._should_trigger = False
      return None

  def after_run(self, run_context, run_values):
    if self._should_trigger:
      results = run_values.results["result"]
      global_step = run_values.results["global_step"]
      elapsed_time, l_step = self._timer.update_last_triggered_step(self._counter)
      if elapsed_time is not None:
        gqps = (global_step - self._last_gstep) / elapsed_time
        lqps = l_step / elapsed_time
        s = "<time={}> <gstep={}> <lstep={}> <gqps={:.3f}> <lqps={:.3f}>".format(
            str(datetime.datetime.now()), global_step, self._counter, gqps, lqps)
        for i in zip(self._metrics, results):
          s += " <{}={}>".format(i[0][0], i[1])
        tf.logging.info(s)
      self._last_gstep = global_step
    self._counter += self._counter_increment
