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
from collections import OrderedDict

from tensorflow.python.platform import tf_logging

from efl.framework import task_scope
from efl.framework.common_define import *
from efl.stage.loop import LoopStage
from efl.utils import config

def iterate_train_and_eval(*args, **kwargs):
  def _wrapper(model):
    task_specs = kwargs.pop("task_specs", None)
    if not task_specs:
      raise ValueError("must have task_specs param")
    if not isinstance(task_specs, dict):
      raise ValueError("task_specs must be a dict")
    pipe_max_iter = kwargs.pop("pipe_max_iter", sys.maxsize)
    train_stop_at_any_finish = kwargs.pop("train_stop_at_any_finish", False)
    task_stages = OrderedDict()
    for task, params in task_specs.items():
      if not isinstance(params, dict):
        raise ValueError("task_spec's params must be a dict")
      max_iter = params.pop("max_iter", sys.maxsize)
      train_step = params.pop("train_step", None)
      has_eval_step = 'eval_step' in params
      eval_step = params.pop("eval_step", None)
     
      task_stages[task] = [LoopStage(model.train_op(task), True, train_step)]
      if has_eval_step:
        task_stages[task] += [LoopStage(model.eval_op(task), False, eval_step)]
    cur_iter = 0
    while True:
      for task, task_stage in task_stages.items():
        with task_scope.task_scope(mode=MODE.TRAIN, task=task):
          if not task_stage[0].finish:
            model.run_stage(
              task + "_train", task_stage[0], 
              feed_dict={model.training_flag:True})
            if task_stage[0].finish:
              tf_logging.info("task[{}] train finish".format(task))
          all_finish = True
          if train_stop_at_any_finish and task_stage[0].finish:
            break
          for ts in task_stages:
            if not task_stages[ts][0].finish:
              all_finish = False
              break
          if all_finish:
            tf_logging.info("all task train finish, iterate train fn complete")
            break
      if all_finish:
        break
      cur_iter += 1
      if cur_iter >= pipe_max_iter:
        tf_logging.info("exceed max iter[{}], cotrain fn complete".format(pipe_max_iter))
        break

    tf_logging.info('eval ...')
    for task, task_stage in task_stages.items():
      if len(task_stage) > 1:
        with task_scope.task_scope(mode=MODE.EVAL, task=task):
          model.run_stage(
            task + "_eval", task_stage[1], 
            feed_dict={model.training_flag:False})
  return _wrapper

def iterate_train(*args, **kwargs):
  def _wrapper(model):
    task_specs = kwargs.pop("task_specs", None)
    if not task_specs:
      raise ValueError("must have task_specs param")
    if not isinstance(task_specs, dict):
      raise ValueError("task_specs must be a dict")
    pipe_max_iter = kwargs.pop("pipe_max_iter", sys.maxsize)
    train_stop_at_any_finish = kwargs.pop("train_stop_at_any_finish", False)
    task_stages = OrderedDict()
    for task, params in task_specs.items():
      if not isinstance(params, dict):
        raise ValueError("task_spec's params must be a dict")
      max_iter = params.pop("max_iter", sys.maxsize)
      train_step = params.pop("train_step", None)
      task_stages[task] = [LoopStage(model.train_op(task), True, train_step)]
      
    cur_iter = 0
    while True:
      for task, task_stage in task_stages.items():
        with task_scope.task_scope(mode=MODE.TRAIN, task=task):
          if not task_stage[0].finish:
            model.run_stage(
              task + "_train", task_stage[0], 
              feed_dict={model.training_flag:True})
            if task_stage[0].finish:
              tf_logging.info("task[{}] train finish".format(task))
          all_finish = True
          if train_stop_at_any_finish and task_stage[0].finish:
            break
          for ts in task_stages:
            if not task_stages[ts][0].finish:
              all_finish = False
              break
          if all_finish:
            tf_logging.info("all task train finish, iterate train fn complete")
            break
      if all_finish:
        break
      cur_iter += 1
      if cur_iter >= pipe_max_iter:
        tf_logging.info("exceed max iter[{}], cotrain fn complete".format(pipe_max_iter))
        break
  return _wrapper


