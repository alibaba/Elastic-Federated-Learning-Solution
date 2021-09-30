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
from utils.ops import build_mlp_layer, poly
from utils.optimizer_fn import custom_scope_optimizer
from utils.procedure_fn import iterate_train_and_eval

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

POLY_ARC_REG_W_ST = 0.
POLY_ARC_REG_W_ED = 5.
POLY_L1_PERIOD_ST = 0.
POLY_L1_PERIOD_EN = 1.
POLY_MAX_STEPS = 5000
POLY_POWER = 1.

FED_LEADER_LAYER_CNT = 3
FED_FOLLOWER_LAYER_CNT = 2
KEEP_EDGE_THRESHOLD = 0.4

BATCH_SIZE = 1024
NUM_EPOCHS = 1
FEATURE_NUM = 21 
EMB_DIM = 8
BUCKET_SIZE = 5000
COMBINER = "mean"
LOG_STEPS = 1

DNN_LR = 0.002
DNN_TRAIN_GROUP_STEP = 1

NAS_LR = 0.001
NAS_TRAIN_GROUP_STEP = 1
NAS_EVAL_GROUP_STEP = None

JOB_NAME = "FL_hierarchical"

def input_fn(model, mode, task):
  if mode == efl.MODE.TRAIN:
    dataio = efl.data.FederalDataIO(config.get_data_path(mode),
                                    BATCH_SIZE,
                                    model.communicator,
                                    model.federal_role,
                                    efl.get_task_index(), # worker index
                                    efl.get_worker_num(), # worker num
                                    num_epochs=NUM_EPOCHS,
                                    data_mode=config.get_data_mode())
  elif mode == efl.MODE.EVAL:
    dataio = efl.data.FederalDataIO(config.get_data_path(mode),
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

def build_nas_block(input, name, dim, scope, concat_coe, targets):
  with tf.variable_scope(scope, reuse=tf.AUTO_REUSE):
    inners = [build_mlp_layer(name + "_pre", input, dim, activation_fn=tf.nn.leaky_relu)]
    inners += [concat_coe[i] * targets[i] for i in range(len(targets))]
    c_i = tf.concat(inners, axis=-1)
    out = build_mlp_layer(name, c_i, dim, activation_fn=None)
  return out

def model_fn(model, sample, mode, task):
  # recv hidden layers' tensor from follower
  with tf.variable_scope("dnn", reuse=tf.AUTO_REUSE):
    f_fc1 = model.recv('fc1', dtype=tf.float32, require_grad=(mode == efl.MODE.TRAIN))
    f_fc1 = tf.reshape(f_fc1, [-1, 32])
    f_fc2 = model.recv('fc2', dtype=tf.float32, require_grad=(mode == efl.MODE.TRAIN))
    f_fc2 = tf.reshape(f_fc2, [-1, 32])
    f_fcs = [f_fc1, f_fc2]
    f_fcs = [build_mlp_layer("pre_f_{}".format(idx), target, 128) for idx, target in enumerate(f_fcs)]

  # build hidden layer interact matrix
  with tf.variable_scope("nas", reuse=tf.AUTO_REUSE):
    concat_mat = tf.get_variable(name="concat_mat",
                                 shape=(FED_LEADER_LAYER_CNT, FED_FOLLOWER_LAYER_CNT),
                                 initializer=tf.zeros_initializer())
    concat_mat = tf.nn.sigmoid(concat_mat)
    if mode == efl.MODE.EVAL:
      concat_mat = tf.where(tf.greater(concat_mat, KEEP_EDGE_THRESHOLD),
                            concat_mat,
                            tf.zeros_like(concat_mat))

  inputs = [sample['emb' + str(i)] for i in range(FEATURE_NUM)]
  labels = tf.cast(sample['label'], tf.float32)

  # build edge
  input = tf.concat(inputs, axis=1)
  fc1 = build_nas_block(input, "fc1", 128, "dnn", concat_mat[0, :], f_fcs)
  fc2 = build_nas_block(fc1, "fc2", 128, "dnn", concat_mat[1, :], f_fcs)
  fc3 = build_nas_block(fc2, "fc3", 128, "dnn", concat_mat[2, :], f_fcs)

  with tf.variable_scope("dnn", reuse=tf.AUTO_REUSE):
    logits =  build_mlp_layer("logits", fc3, 1, activation_fn=None)
  pred = tf.nn.sigmoid(logits)

  # add metrics
  model.add_metric('task', task, mode=mode, task=task)
  mode_str = "train" if mode==efl.MODE.TRAIN else "eval"
  model.add_metric('mode', mode_str, mode=mode, task=task)
  _, auc = tf.metrics.auc(labels, pred, name=task+"/"+mode_str)
  model.add_metric('auc', auc, mode=mode, task=task)
  model.add_metric('concat_mat', concat_mat, mode=mode, task=task)

  loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels=labels, logits=logits))
  if mode == efl.MODE.TRAIN:
    model.add_metric('loss', loss, mode=mode, task=task)
  return loss, concat_mat

def loss_fn_dnn(model, sample, mode, task):
  with tf.variable_scope(JOB_NAME):
    loss, _ =  model_fn(model, sample, mode, task)
    return loss

def loss_fn_nas(model, sample, mode, task):

  with tf.variable_scope(JOB_NAME):
    loss, concat_mat =  model_fn(model, sample, mode, task)
    nas_entropy = -concat_mat * tf.log(concat_mat + 1e-8) - (1.0 - concat_mat) * tf.log(1.0 - concat_mat + 1e-8)
    nas_entropy = tf.reduce_mean(nas_entropy)
    lstep = tf.Variable(initial_value=0, name="lstep", trainable=False, dtype=tf.int64)
    lstep_inc = lstep.assign_add(1)
    with tf.control_dependencies([lstep_inc]):
      poly_w = poly(POLY_ARC_REG_W_ST,
                    POLY_ARC_REG_W_ED,
                    lstep,
                    tf.constant(POLY_MAX_STEPS, dtype=tf.int64),
                    (POLY_L1_PERIOD_ST, POLY_L1_PERIOD_EN),
                    POLY_POWER)
    return loss + poly_w * nas_entropy

def build_model():
  model = efl.FederalModel()
  # build dnn task
  with efl.task_scope(mode=efl.MODE.TRAIN, task="dnn"):
    model.input_fn(functools.partial(input_fn, task="dnn"))
    model.loss_fn(functools.partial(loss_fn_dnn, mode=efl.MODE.TRAIN, task="dnn"))
    scope_optimizers = {
      '{}/nas'.format(JOB_NAME): tf.train.AdamOptimizer(0.),
      '{}/dnn'.format(JOB_NAME): tf.train.AdamOptimizer(DNN_LR)
    }
    model.optimizer_fn(custom_scope_optimizer(scope_optimizers))
  
  # build nas task
  with efl.task_scope(mode=efl.MODE.TRAIN, task="nas"):
    model.input_fn(functools.partial(input_fn, task="nas"))
    model.loss_fn(functools.partial(loss_fn_nas, mode=efl.MODE.TRAIN, task="nas"))
    model.eval_fn(functools.partial(loss_fn_nas, mode=efl.MODE.EVAL, task="nas"))
    scope_optimizers = {
      '{}/nas'.format(JOB_NAME): tf.train.AdamOptimizer(NAS_LR),
      '{}/dnn'.format(JOB_NAME): tf.train.AdamOptimizer(0.)
    }
    model.optimizer_fn(custom_scope_optimizer(scope_optimizers))
  model.compile()
  return model

if __name__ == '__main__':
  model = build_model()
  task_specs = OrderedDict()
  task_specs['dnn'] = {"train_step": DNN_TRAIN_GROUP_STEP}
  task_specs['nas'] = {"train_step": NAS_TRAIN_GROUP_STEP, "eval_step": NAS_EVAL_GROUP_STEP}
  model.fit(iterate_train_and_eval(task_specs=task_specs, train_stop_at_any_finish=True),
            log_step=LOG_STEPS, 
            project_name=JOB_NAME)
  
