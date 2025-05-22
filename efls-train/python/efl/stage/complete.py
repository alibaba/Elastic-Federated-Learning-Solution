#!/usr/bin/env python
# encoding: utf-8
'''
@author: renjian
@contact: renjian04@meituan.com
@file: complete.py
@time: 2022/4/30 9:31 上午
@desc: 
'''

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
import os
import tensorflow.compat.v1 as tf
from tensorflow.python.framework import errors
from tensorflow.python.training import training_util
from tensorflow.python.training.sync_replicas_optimizer import _SyncReplicasOptimizerHook
from efl.utils import config
from efl import exporter
from efl.framework import stage
from efl.framework import hook_manager

@exporter.export("stage.CompleteStage")


class CompleteStage(stage.Stage):
  def __init__(self, run_ops):
    self._finish = False
    self._run_ops = run_ops
    self.idx = config.get_task_index()

  @property
  def finish(self):
    return self._finish

  def run(self, feed_dict={}):
    out = []
    try :
      while True:
        if self.sess.should_stop():
          tf.logging.info("sess.should_stop is True, CompleteStage finish")
          self._finish = True
          break
        rs = self.sess.run(self._run_ops, feed_dict = feed_dict)
        for r in rs[-1]:
          out.append(','.join(r.reshape(-1).astype(str)))
    except (errors.OutOfRangeError, StopIteration):
      tf.logging.info("catch OutOfRangeError or StopIteration, LoopStage finish")
      self._finish = True
      self._deal_with_sync_optimize_hook()
    infer_dir = config.get_infer_dir()
    if infer_dir:
      if self.idx == 0:
        if tf.gfile.Exists(infer_dir):
          tf.gfile.DeleteRecursively(infer_dir)
          tf.gfile.MakeDirs(infer_dir)
        else:
          tf.gfile.MakeDirs(infer_dir)
      filename = 'part_{}'.format(self.idx)
      example_filename = os.path.join(infer_dir, filename)
      with tf.gfile.GFile(example_filename, 'w') as embedding_file:
        embedding_file.write('\n'.join(out))


  def _deal_with_sync_optimize_hook(self):
    for h in hook_manager.get_hook_manager().get_running_hooks():
      if isinstance(h, _SyncReplicasOptimizerHook):
        h.end(self.sess._tf_sess())
        hook_manager.get_hook_manager().hook_end(h)
