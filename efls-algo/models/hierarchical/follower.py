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
from utils.ops import build_mlp_layer
from utils.optimizer_fn import custom_scope_optimizer
from utils.procedure_fn import iterate_train_and_eval

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

BATCH_SIZE = 1024
NUM_EPOCHS = 1
INPUT_DIMS = 10
LOG_STEPS = 1

LR = 0.02
DNN_TRAIN_GROUP_STEP = 1
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
  dataio.fixedlen_feature('dense', INPUT_DIMS, dtype=tf.float32)
  features = dataio.read()

  # add dataio hook
  model.add_hooks([dataio.get_hook()], mode=mode, task=task)

  # declare feature columns
  columns = {"emb": [tf.feature_column.numeric_column('dense', INPUT_DIMS)]}

  return efl.FederalSample(features, columns, model.federal_role, model.communicator, sample_id_name='sample_id')

def model_fn(model, sample, mode, task):
  input = sample['emb']
  with tf.variable_scope("dnn"):
    fc1 = build_mlp_layer("fc1", input, 32, activation_fn=tf.nn.leaky_relu)
    fc2 = build_mlp_layer("fc2", fc1, 32, activation_fn=tf.nn.leaky_relu)
    # send dnn hidden layer tensor to leader
    require_grad = mode == efl.MODE.TRAIN and task == "dnn"
    model.send('fc1', fc1, require_grad=require_grad, mode=mode)
    model.send('fc2', fc2, require_grad=require_grad, mode=mode)

    model.add_metric('task', task, mode=mode, task=task)
    model.add_metric('mode', "train" if mode==efl.MODE.TRAIN else "eval", mode=mode, task=task)
  
    return fc2

def loss_fn(model, sample, mode, task):
  with tf.variable_scope(JOB_NAME):
    return model_fn(model, sample, mode, task)

def build_model():
  model = efl.FederalModel()
  # build dnn task
  with efl.task_scope(mode=efl.MODE.TRAIN, task="dnn"):
    model.input_fn(functools.partial(input_fn, task="dnn"))
    model.loss_fn(functools.partial(loss_fn, mode=efl.MODE.TRAIN, task="dnn"))
    scope_optimizers = {
      '{}/dnn'.format(JOB_NAME): tf.train.AdamOptimizer(LR)
    }
    model.optimizer_fn(custom_scope_optimizer(scope_optimizers))
  
  # build nas task
  with efl.task_scope(mode=efl.MODE.TRAIN, task="nas"):
    model.input_fn(functools.partial(input_fn, task="nas"))
    model.loss_fn(functools.partial(loss_fn, mode=efl.MODE.TRAIN, task="nas"))
    model.eval_fn(functools.partial(loss_fn, mode=efl.MODE.EVAL, task="nas"))
    # disable follower's parameter updating when in nas step
    scope_optimizers = {
      '{}/dnn'.format(JOB_NAME): tf.train.GradientDescentOptimizer(0.)
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
