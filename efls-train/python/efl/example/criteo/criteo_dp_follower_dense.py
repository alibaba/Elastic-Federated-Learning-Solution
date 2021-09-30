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

id_nums = [1400, 500, 2000000, 660000, 300, 20, 10000, 600, 3,
           50000, 4800, 2000000, 3000, 20, 10000, 1400000, 9,
           4500, 1700000, 15, 120000]

def input_fn(model, mode):
  if mode == efl.MODE.TRAIN:
    dataio = efl.data.FederalDataIO("./follower_train", 1000, model.communicator, model.federal_role, 0, 1, data_mode='local', num_epochs=10)
  else:
    dataio = efl.data.FederalDataIO("./follower_test", 1000, model.communicator, model.federal_role, 0, 1, data_mode='local', num_epochs=10)
  dataio.fixedlen_feature('sample_id', 1, dtype=tf.int64)
  for i in range(21):
    dataio.fixedlen_feature('feature' + str(i), 1, dtype=tf.string)
  features = dataio.read()
  model.add_hooks([dataio.get_hook()])
  columns = {
      'embedding': [
          tf.feature_column.embedding_column(
              tf.feature_column.categorical_column_with_hash_bucket('feature' + str(i), id_nums[i]),
              dimension=8, combiner='mean')
          for i in range(21)]}
  return efl.FederalSample(features, columns, model.federal_role, model.communicator, sample_id_name='sample_id',
                               name='train' if mode == efl.MODE.TRAIN else 'eval')

def model_fn(model, sample, is_training):
  inputs = tf.reshape(sample['embedding'], [-1, 168])
  if is_training:
    model.send('embedding_train', inputs, require_grad=True)
  else:
    model.send('embedding_test', inputs, mode=efl.MODE.EVAL, require_grad=False)
  return inputs

def loss_fn(model, sample):
  with tf.variable_scope('fed_criteo', reuse=tf.AUTO_REUSE):
    return model_fn(model, sample, True)

def eval_fn(model, sample):
  with tf.variable_scope('fed_criteo', reuse=tf.AUTO_REUSE):
    return model_fn(model, sample, False)

DNN = efl.FederalModel()
DNN.input_fn(input_fn)
DNN.loss_fn(loss_fn)
DNN.eval_fn(eval_fn)
DNN.optimizer_fn(efl.optimizer_fn.optimizer_setter(tf.train.AdamOptimizer(0.01)))
DNN.compile()
DNN.fit(efl.procedure_fn.train_and_evaluate(train_step=8000, eval_step=3800, max_iter=10),
        log_step=1000,
        project_name='fed_criteo')
