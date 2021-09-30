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

import time
import pickle
import numpy as np
import bisect

import tensorflow.compat.v1 as tf
from tensorflow.python.framework import ops

from efl import lib
from efl.framework import stage_combiner
from efl.framework import stage
from efl.framework.common_define import *

class StageManager(object):
  def __init__(self, root_scope, device, worker_id, worker_num, project_name, name):
    self._idx = 0
    self._worker_num = worker_num
    self._worker_id = worker_id
    self._monitored_sess = None
    with tf.device(device):
      with tf.variable_scope(root_scope):
        with tf.variable_scope(name):
          self._stage_name_var = tf.get_variable(
              "stage_name", [0], tf.string,
              initializer=tf.constant_initializer(""), use_resource=True)
          self._stage_result_var = tf.get_variable(
              "stage_result", [0, worker_num], tf.string,
              initializer=tf.constant_initializer(""), use_resource=True)
          self._stage_order_var = tf.get_variable(
              "stage_order", [0, worker_num], tf.int64,
              initializer=tf.constant_initializer(0), use_resource=True)
          self._stage_status_var = tf.get_variable(
              "stage_status", [0, worker_num], tf.int64,
              initializer=tf.constant_initializer(0), use_resource=True)
          self._project_name_var = tf.get_variable(
              "project_name", [], tf.string,
              initializer=tf.constant_initializer(project_name),
              use_resource=True)
          self._project_name = project_name
          self._stage_idx = tf.placeholder(tf.int64)
          self._stage_name = tf.placeholder(tf.string)
          self._stage_result = tf.placeholder(tf.string)
          self._finish_ratio = tf.placeholder(tf.float32)
          self._stage_status = lib.ops.stage_status(
              self._stage_name_var.handle, self._stage_result_var.handle,
              self._stage_order_var.handle, self._stage_status_var.handle,
              self._stage_idx, self._stage_name, 
            self._finish_ratio, worker_id, worker_num)
          self._stage_update = lib.ops.stage_update(
              self._stage_name_var.handle, self._stage_result_var.handle,
              self._stage_order_var.handle, self._stage_status_var.handle,
              self._stage_idx, self._stage_name, self._stage_result,
              worker_id, worker_num)

  def init_arg(self, sess):
    self._tf_sess = sess
    self._idx = 0
    self._running = False
    self._in_stage = False
    prjname = self._tf_sess.run(self._project_name_var)
    if prjname.decode() != self._project_name:
      tf.logging.warning(
          "Latest project is %s, now is %s. clear it.",
          prjname, self._project_name)
      self._tf_sess.run([
        self._stage_name_var.initializer,
        self._stage_result_var.initializer,
        self._stage_order_var.initializer,
        self._stage_status_var.initializer,
        self._project_name_var.initializer
      ])

  def set_monitored_sess(self, sess):
    self._monitored_sess = sess

  def running(self):
    return self._running

  def in_stage(self):
    return self._in_stage

  def stage(self, name, func, interval, *args, **kwargs):
    finish_ratio = kwargs.pop(STAGE_WAIT_RATIO, 1.0)
    if finish_ratio < 0 or finish_ratio > 1.0:
      raise ValueError('{} must in [0, 1.0]'.format(STAGE_WAIT_RATIO))
    if isinstance(func, stage.Stage):
      func = func(*args, **kwargs)
    self._in_stage = True
    try:
      status, stage_result, order = self._tf_sess.run(
          self._stage_status, feed_dict={
            self._stage_idx : self._idx, self._stage_name : name,
            self._finish_ratio: finish_ratio})
      if status == 2:
        self._idx += 1
        stage_result, order = self._get_stage_result(stage_result, order)
        return stage_combiner.combine(
            [pickle.loads(i) for i in stage_result], order)
      self._running = True
      if status == 0:
        rst = func(self._monitored_sess)
        self._tf_sess.run(self._stage_update, feed_dict={
          self._stage_idx : self._idx,
          self._stage_name : name,
          self._stage_result : pickle.dumps(rst)
        })
      while True:
        status, stage_result, order = self._tf_sess.run(
            self._stage_status, feed_dict={
              self._stage_idx : self._idx, self._stage_name : name,
              self._finish_ratio: finish_ratio})
        tf.logging.warning("[StageManager] [name={}] [task finished order=[{}]]".format(
            name, ','.join([str(i) for i in order])))
        if status == 2:
          stage_result, order = self._get_stage_result(stage_result, order)
          if len(order) < self._worker_num:
            tf.logging.warning(
              "[StageManager] [name={}] [finish ratio:{} "
              "exceed threshold:{}, current stage finished]".format(
                name, float(len(order)) / self._worker_num, finish_ratio))          
          rst = stage_combiner.combine(
              [pickle.loads(i) for i in stage_result], order)
          self._idx += 1
          return rst
        else:
          running_tasks = self._get_running_tasks(order)
          tf.logging.info("[StageManager] [name={}] [running tasks=[{}]]".format(
              name, ','.join([str(i) for i in running_tasks])))
        time.sleep(interval)
    finally:
      self._in_stage = False

  def _get_stage_result(self, stage_result, order):
    if -1 not in order:
      return stage_result, order
    r'''deal with partial finish'''
    order_set = set(order)
    unfinished = []
    del_num = 0
    for i in range(len(order)):
      if i not in order:
        unfinished.append(i)
        if isinstance(stage_result, np.ndarray):
          stage_result = np.delete(stage_result, i-del_num, 0)
        elif isinstance(stage_result, list):
          del stage_result[i-del_num]
        else:
          return stage_result, order
        del_num += 1
    unfinished.sort()
    new_order = []
    for i in order:
      if i != -1:
        idx = bisect.bisect_left(unfinished, i)
        new_order.append(i-idx)
    return stage_result, new_order

  def _get_running_tasks(self, order):
    workers = [False] * self._worker_num
    for i in order:
      if i != -1:
        workers[i] = True
    return [i for i, done in enumerate(workers) if not done]
