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

import pandas as pd
import tensorflow.compat.v1 as tf
import efl

def input_fn(model, mode):
  if mode == efl.MODE.TRAIN:
    dataio = efl.data.FederalDataIO("./leader_train", 1000, model.communicator, model.federal_role, 0, 1, data_mode='local', num_epochs=10)
  else:
    dataio = efl.data.FederalDataIO("./leader_test", 1000, model.communicator, model.federal_role, 0, 1, data_mode='local', num_epochs=10)
  dataio.fixedlen_feature('sample_id', 1, dtype=tf.int64)
  dataio.fixedlen_feature('label', 1, dtype=tf.int64)
  dataio.fixedlen_feature('dense', 10, dtype=tf.float32)
  features = dataio.read()
  model.add_hooks([dataio.get_hook()])
  columns = {
      'dense': [tf.feature_column.numeric_column('dense', 10)],
      'label': [tf.feature_column.numeric_column('label', 1)]}
  return efl.FederalSample(features, columns, model.federal_role, model.communicator, sample_id_name='sample_id',
                               name = 'train' if mode == efl.MODE.TRAIN else 'eval')

def model_fn(model, sample, is_training):
  if is_training:
    embedding = model.recv('embedding_train', dtype=tf.float32, require_grad=True, shape=[-1, 168])
  else:
    embedding = model.recv('embedding_test', dtype=tf.float32, require_grad=False, shape=[-1, 168])
  inputs = tf.reshape(sample['dense'], [-1, 10])
  inputs = tf.concat([inputs, embedding], axis=1)
  labels = tf.cast(tf.squeeze(sample['label']), tf.int64)
  y = tf.layers.dense(inputs, 512, activation='relu')
  y = tf.layers.dense(inputs, 64, activation='relu')
  y = tf.layers.dense(y, 16, activation='relu')
  logits = tf.layers.dense(y, 2)
  loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=labels, logits=logits)
  if is_training:
    model.add_metric('loss', tf.reduce_mean(loss), efl.MODE.TRAIN)
    return loss
  else:
    prediction = tf.argmax(logits, axis=-1)
    accuracy = tf.metrics.accuracy(labels, prediction)
    model.add_metric('accuracy', accuracy, efl.MODE.EVAL)
    return accuracy[1]

def loss_fn(model, sample):
  with tf.variable_scope('fed_criteo'):
    return model_fn(model, sample, True)

def eval_fn(model, sample):
  with tf.variable_scope('fed_criteo', reuse=tf.AUTO_REUSE):
    return model_fn(model, sample, False)

DNN = efl.FederalModel()
DNN.input_fn(input_fn)
DNN.loss_fn(loss_fn)
DNN.eval_fn(eval_fn)
DNN.optimizer_fn(efl.optimizer_fn.optimizer_setter(efl.DPAdamGaussianOptimizer(
    l2_norm_clip=1.0, noise_multiplier=1.0, learning_rate=0.01)))
DNN.compile(opt_config={'BACKEND_MODE': 'unnoise'})
#DNN.optimizer_fn(efl.optimizer_fn.optimizer_setter(tf.train.AdamOptimizer(0.01)))
#DNN.compile()
DNN.fit(efl.procedure_fn.train_and_evaluate(train_step=8000, eval_step=3800, max_iter=10),
        log_step=1000,
        project_name='fed_criteo')
