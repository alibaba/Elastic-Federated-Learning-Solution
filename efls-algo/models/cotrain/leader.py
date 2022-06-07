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

import os
import functools
import sys
sys.path.append(os.getcwd())

from collections import OrderedDict

import numpy as np
import tensorflow.compat.v1 as tf

import efl

from utils import config
from utils.ops import build_mlp_layer, mlp_gate, poly
from utils.optimizer_fn import custom_scope_optimizer
from utils.procedure_fn import iterate_train_and_eval, iterate_train

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
BATCH_SIZE = 1024
NUM_EPOCHS = 1
FEATURE_NUM = 21 
EMB_DIM = 8
BUCKET_SIZE = 5000
COMBINER = "mean"
LOG_STEPS = 1

LOCAL_TRAIN_LR = 0.001
LOCAL_TRAIN_GROUP_STEP = 1

FL_TRAIN_LR = 0.001
FL_TRAIN_GROUP_STEP = 1
FL_EVAL_GROUP_STEP = None

JOB_NAME = "FL_cotrain"


def input_fn_local(model, mode, task):
  if mode == efl.MODE.TRAIN:
    data_mode=config.get_data_mode()
    dataio = efl.data.DataIO(config.get_data_local_path(efl.MODE.TRAIN),
                                        BATCH_SIZE,
                                        efl.get_task_index(), # worker index
                                        efl.get_worker_num(), # worker num
                                        num_epochs=NUM_EPOCHS
                                        )
  elif mode == efl.MODE.EVAL:
    dataio = efl.data.DataIO(config.get_data_local_path(efl.MODE.TRAIN),
                                        BATCH_SIZE,      
                                        efl.get_task_index(), # worker index
                                        efl.get_worker_num(), # worker num
                                        num_epochs=1)
  else:
    raise TypeError("unknowed run mode: %s" % str(mode))

  # registe features in data source
  dataio.fixedlen_feature('sample_id', 1, dtype=tf.int64)
  for i in range(FEATURE_NUM):
    dataio.fixedlen_feature('feature' + str(i), 1, dtype=tf.string)
  dataio.fixedlen_feature('label', 1, dtype=tf.int64)
  features = dataio.read()

  # add dataio hook
  model.add_hooks([dataio.get_hook()], mode=mode, task=task)

  # declare feature columns
  columns = {"label": [tf.feature_column.numeric_column('label', 1)]}
  for i in range(FEATURE_NUM):
    columns.update({"emb" + str(i) : [tf.feature_column.embedding_column(
                 tf.feature_column.categorical_column_with_hash_bucket(
                     'feature' + str(i), BUCKET_SIZE), dimension=EMB_DIM, combiner=COMBINER)]})

  with tf.variable_scope("{}/dnn".format(JOB_NAME), reuse=tf.AUTO_REUSE):
    return efl.Sample(features, columns)


def input_fn_fl(model, mode, task):
  if mode == efl.MODE.TRAIN:
    # config.get_data_path(mode)
    data_mode=config.get_data_mode()
    dataio = efl.data.FederalDataIO(config.get_data_path(efl.MODE.TRAIN),
                                        BATCH_SIZE,
                                        model.communicator,
                                        model.federal_role,
                                        efl.get_task_index(), # worker index
                                        efl.get_worker_num(), # worker num
                                        num_epochs=NUM_EPOCHS,
                                        data_mode=config.get_data_mode()
                                        )
  elif mode == efl.MODE.EVAL:
    dataio = efl.data.FederalDataIO(config.get_data_path(efl.MODE.TRAIN),
                                        BATCH_SIZE,
                                        model.communicator,
                                        model.federal_role,
                                        efl.get_task_index(), # worker index
                                        efl.get_worker_num(), # worker num
                                        num_epochs=1,
                                        data_mode=config.get_data_mode())
  else:
    raise TypeError("unknowed run mode: %s" % str(mode))

  # registe features in data source
  dataio.fixedlen_feature('sample_id', 1, dtype=tf.int64)
  for i in range(FEATURE_NUM):
    dataio.fixedlen_feature('feature' + str(i), 1, dtype=tf.string)
  dataio.fixedlen_feature('label', 1, dtype=tf.int64)
  features = dataio.read()

  # add dataio hook
  model.add_hooks([dataio.get_hook()], mode=mode, task=task)

  # declare feature columns
  columns = {"label": [tf.feature_column.numeric_column('label', 1)]}
  for i in range(FEATURE_NUM):
    columns.update({"emb" + str(i) : [tf.feature_column.embedding_column(
                 tf.feature_column.categorical_column_with_hash_bucket(
                     'feature' + str(i), BUCKET_SIZE), dimension=EMB_DIM, combiner=COMBINER)]})

  with tf.variable_scope("{}/dnn".format(JOB_NAME), reuse=tf.AUTO_REUSE):
    return efl.FederalSample(features, columns, model.federal_role, model.communicator, sample_id_name='sample_id')

def build_gate_block(inputs, name_prefix, targets, tgt_dims, scope):
  all_gated_tensor = []
  with tf.variable_scope(scope, reuse=tf.AUTO_REUSE):
    for l_idx, input in enumerate(inputs):
      gated_tensors = []
      for j_idx, (tgt, tgt_dim) in enumerate(zip(targets, tgt_dims)):
        input_m = build_mlp_layer("{}_{}_{}".format(name_prefix, l_idx, j_idx),
                                input, tgt_dim, activation_fn=None)
        gate = mlp_gate([input_m, tgt], [1])
        gated_tensors.append(gate * input_m + (1 - gate) * tgt)
      all_gated_tensor.append(gated_tensors)
  return all_gated_tensor

def model_fn_fl(model, sample, mode, task):
  # recv hidden layers' tensor from follower
  f_fc1 = model.recv('fc1', dtype=tf.float32, require_grad=(mode == efl.MODE.TRAIN))
  f_fc1 = tf.reshape(f_fc1, [-1, 32])

  inputs = [sample['emb' + str(i)] for i in range(FEATURE_NUM)]
  labels = tf.cast(sample['label'], tf.float32)

  # [M, N]
  gate_blocks = build_gate_block(inputs, "gate_block", [f_fc1], [32], "gate_block")
  input = tf.concat(tf.nest.flatten(gate_blocks), axis=1)

  fc1 = build_mlp_layer("fc1_fl", input, 256)
  fc2 = build_mlp_layer("fc2_fl", fc1, 128)
  logits =  build_mlp_layer("pred_fl", fc2, 1, activation_fn=None)
  pred = tf.nn.sigmoid(logits)

  # add metrics
  model.add_metric('task', task, mode=mode, task=task)
  mode_str = "train" if mode==efl.MODE.TRAIN else "eval"
  model.add_metric('mode', mode_str, mode=mode, task=task)
  _, auc = tf.metrics.auc(labels, pred, name=mode_str)
  model.add_metric('auc', auc, mode=mode, task=task)

  loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels=labels, logits=logits))
  if mode == efl.MODE.TRAIN:
    model.add_metric('loss', loss, mode=mode, task=task)

  return loss

def model_fn_local(model, sample, mode, task):
  inputs = [sample['emb' + str(i)] for i in range(FEATURE_NUM)]
  labels = tf.cast(sample['label'], tf.float32)

  input = tf.concat(inputs, axis=1)
  fc1 = build_mlp_layer("fc1", input, 256)
  fc2 = build_mlp_layer("fc2", fc1, 128)
  logits =  build_mlp_layer("pred", fc2, 1, activation_fn=None)
  pred = tf.nn.sigmoid(logits)

  # add metrics
  model.add_metric('task', task, mode=mode, task=task)
  mode_str = "train" if mode==efl.MODE.TRAIN else "eval"
  model.add_metric('mode', mode_str, mode=mode, task=task)
  _, auc = tf.metrics.auc(labels, pred, name=mode_str)
  model.add_metric('auc', auc, mode=mode, task=task)

  loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels=labels, logits=logits))
  if mode == efl.MODE.TRAIN:
    model.add_metric('loss', loss, mode=mode, task=task)

  return loss

def loss_fn_fl(model, sample, mode, task):
  with tf.variable_scope(JOB_NAME, reuse=tf.AUTO_REUSE):
    loss =  model_fn_fl(model, sample, mode, task)
    return loss

def loss_fn_local(model, sample, mode, task):
  with tf.variable_scope(JOB_NAME, reuse=tf.AUTO_REUSE):
    loss =  model_fn_local(model, sample, mode, task)
    return loss

def build_model():
  model = efl.FederalModel()
  # build local train task
  with efl.task_scope(mode=efl.MODE.TRAIN, task="local_train"):
    model.input_fn(functools.partial(input_fn_local,task="local_train"))
    model.loss_fn(functools.partial(loss_fn_local, mode=efl.MODE.TRAIN, task="local_train"))
    scope_optimizers = {
      'global'.format(JOB_NAME): tf.train.AdamOptimizer(LOCAL_TRAIN_LR)
    }
    model.optimizer_fn(custom_scope_optimizer(scope_optimizers))
  
  # build fl train task
  with efl.task_scope(mode=efl.MODE.TRAIN, task="fl_train"):
    model.input_fn(functools.partial(input_fn_fl , task="fl_train"))
    model.loss_fn(functools.partial(loss_fn_fl, mode=efl.MODE.TRAIN, task="fl_train"))
    model.eval_fn(functools.partial(loss_fn_fl, mode=efl.MODE.EVAL, task="fl_train"))
    scope_optimizers = {
      'global'.format(JOB_NAME): tf.train.AdamOptimizer(FL_TRAIN_LR)
    }
    model.optimizer_fn(custom_scope_optimizer(scope_optimizers))
  model.compile()
  return model

if __name__ == '__main__':
  model = build_model()
  task_specs = OrderedDict()
  task_specs['local_train'] = {"train_step": LOCAL_TRAIN_GROUP_STEP}
  task_specs['fl_train'] = {"train_step": FL_TRAIN_GROUP_STEP, "eval_step": FL_EVAL_GROUP_STEP}
  model.fit(iterate_train(task_specs=task_specs),log_step=LOG_STEPS, project_name=JOB_NAME)

