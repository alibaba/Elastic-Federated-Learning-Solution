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
import random
import bisect

from tensorflow.python.platform import tf_logging

from efl import exporter
from efl.utils import config
from efl.stage.loop import LoopStage
from efl.framework import task_scope
from efl.framework.common_define import *

r'''builtin procedure fn'''
@exporter.export('procedure_fn.train')
def train(*args, **kwargs):
  def _wrapper(model):
    max_step = kwargs.pop("max_step", None)
    train_stage = LoopStage(model.train_op(), True, step=max_step)    
    with task_scope.task_scope(mode=MODE.TRAIN):
      model.run_stage(
        "train", train_stage, 
        feed_dict={model.training_flag:True})
    tf_logging.info("train fn complete")
  return _wrapper

@exporter.export('procedure_fn.eval')
def eval(*args, **kwargs):
  def _wrapper(model):
    max_step = kwargs.pop("max_step", None)
    eval_stage = LoopStage(model.eval_op(), False, step=max_step)
    with task_scope.task_scope(mode=MODE.EVAL):
      model.run_stage(
        "eval", eval_stage,
        feed_dict={model.training_flag:False})
    tf_logging.info("eval fn complete")
  return _wrapper

@exporter.export('procedure_fn.train_and_evaluate')
def train_and_evaluate(*args, **kwargs):
  def _wrapper(model):
    train_step = kwargs.pop("train_step", None)
    eval_step = kwargs.pop("eval_step", None)
    train_interval = kwargs.pop("train_interval", None)
    eval_interval = kwargs.pop("eval_interval", None)
    max_iter = kwargs.pop("max_iter", sys.maxsize)
    train_stage = LoopStage(model.train_op(), True, train_step, train_interval)
    eval_stage = LoopStage(model.eval_op(), False, eval_step, eval_interval)    
    def reset_metrics_stage(sess):
      if config.is_chief():
        sess._tf_sess().run(model.metric_variables_initializer)
    cur_iter = 0
    while True:
      tf_logging.info("train_and_evaluate start run iter[{}]".format(cur_iter))
      with task_scope.task_scope(mode=MODE.TRAIN):
        model.run_stage(
          "train", train_stage, 
          feed_dict={model.training_flag:True})
      model.run_stage("reset_metrics", reset_metrics_stage)
      with task_scope.task_scope(mode=MODE.EVAL):        
        model.run_stage(
          "eval", eval_stage, 
          feed_dict={model.training_flag:False})
      if train_stage.finish :
        tf_logging.info("train_stage finish, train_and_evaluate fn complete")
        break
      cur_iter += 1
      if cur_iter >= max_iter:
        tf_logging.info("reach max_iter[{}], train_and_evaluate fn complete".format(max_iter))
        break
  return _wrapper

@exporter.export('procedure_fn.cotrain')
def cotrain(*args, **kwargs):
  random.seed(0)
  def _select_task(task_select_ratio):
    tasks = []
    boundaries = []
    for task, ratio in task_select_ratio.items():
      tasks.append(task)
      boundaries.append(ratio if len(boundaries) == 0 else ratio + boundaries[-1])
    if boundaries[-1] != 1.0:
      raise ValueError("sum of task select ratio is not 1.0")
    randnum = random.randint(0, 99)
    return tasks[bisect.bisect_left(boundaries, randnum / 100.0)]

  def _wrapper(model):
    task_select_ratio = kwargs.pop("task_select_ratio", None)
    if not task_select_ratio:
      raise ValueError("must have task_select_ratio param")
    if not isinstance(task_select_ratio, dict):
      raise ValueError("task_select_ratio param must be a dict")
    max_iter = kwargs.pop("max_iter", sys.maxsize)
    train_step = kwargs.pop("train_step", None)
    eval_step = kwargs.pop("eval_step", None)
    task_stages = {}
    for task in task_select_ratio.keys():
      task_stages[task] = (
        LoopStage(model.train_op(task), True, train_step), 
        LoopStage(model.eval_op(task), False, eval_step))
    cur_iter = 0
    while True:
      task = _select_task(task_select_ratio)
      task_stage = task_stages[task]
      with task_scope.task_scope(task=task, mode=MODE.TRAIN):
        if not task_stage[0].finish:
          model.run_stage(
            task + "_train", task_stage[0], 
            feed_dict={model.training_flag:True})
          if task_stage[0].finish:
            tf_logging.info("task[{}] train finish")
        all_finish = True
        for ts in task_stages:
          if not task_stages[ts][0].finish:
            all_finish = False
            break
        if all_finish:
          tf_logging.info("all task train finish, cotrain fn complete")
          break
      with task_scope.task_scope(task=task, mode=MODE.EVAL):
        model.run_stage(
          task + "_eval", task_stage[1], 
          feed_dict={model.training_flag:False})
      cur_iter += 1
      if cur_iter >= max_iter:
        tf_logging.info("exceed max iter[{}], cotrain fn complete".format(max_iter))
        break
  return _wrapper
