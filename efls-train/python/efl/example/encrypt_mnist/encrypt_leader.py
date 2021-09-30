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
import numpy as np
import tensorflow.compat.v1 as tf
import efl

def input_fn(model, mode):
  if mode == efl.MODE.TRAIN:
    dataio = efl.data.FederalDataIO("./leader_train", 256, model.communicator, model.federal_role, 0, 1, data_mode='local')
    dataio.fixedlen_feature('sample_id', 1, dtype=tf.int64)
    dataio.fixedlen_feature('feature', 14*28, dtype=tf.float32)
    dataio.fixedlen_feature('label', 1, dtype=tf.float32)
    features = dataio.read()
    model.add_hooks([dataio.get_hook()])
    columns = {
      "label": [tf.feature_column.numeric_column('label', 1)],
      "emb": [tf.feature_column.numeric_column('feature', 14*28)]}
    return efl.FederalSample(features, columns, model.federal_role, model.communicator, sample_id_name='sample_id')

def model_fn(model, sample):
  input = sample['emb']
  fc1 = tf.layers.dense(input, 128,
    kernel_initializer=tf.truncated_normal_initializer(
      stddev=0.001, dtype=tf.float32))
  passive_layer = efl.privacy.EncryptPassiveLayer(model.communicator, 128, 128, "public_key.json")
  fc1 = passive_layer(fc1)
  fc1 = tf.reshape(fc1, [-1, 256])
  y = tf.layers.dense(
    fc1, 10, kernel_initializer=tf.truncated_normal_initializer(
      stddev=0.001, dtype=tf.float32))
  pred = tf.argmax(y, axis=-1)
  _, accuracy = tf.metrics.accuracy(sample['label'], pred)
  model.add_metric('accuracy', accuracy)
  label = tf.cast(sample['label'], tf.int32)
  label = tf.reshape(label, [-1])
  label = tf.one_hot(label, 10)
  loss = tf.losses.softmax_cross_entropy(label, y)
  return loss

CTR = efl.FederalModel()
CTR.input_fn(input_fn)
CTR.loss_fn(model_fn)
CTR.optimizer_fn(efl.optimizer_fn.optimizer_setter(tf.train.GradientDescentOptimizer(0.001)))
CTR.compile()
CTR.fit(efl.procedure_fn.train(), 
        log_step=1, 
        project_name="train")
