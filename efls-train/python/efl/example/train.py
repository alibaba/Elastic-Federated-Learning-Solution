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

import tensorflow as tf
import efl

def input_fn(model, mode):
  if mode == efl.MODE.TRAIN:
    features = {
      "dense": tf.constant([[1,2]], dtype=tf.float32), 
      "label": tf.constant([[1.0]], dtype=tf.float32),
      "sparse1": tf.constant([[1,2,3,4]], dtype=tf.int64),
      "sparse2": tf.constant([[5,6]], dtype=tf.int64)}
    columns = {
      "deep": [tf.feature_column.numeric_column('dense', 2)],
      "label": [tf.feature_column.numeric_column('label', 1)],
      "emb": [
        tf.feature_column.embedding_column(
          tf.feature_column.categorical_column_with_identity("sparse1", 1000), dimension=8, combiner='mean'),
        tf.feature_column.embedding_column(
          tf.feature_column.categorical_column_with_identity("sparse2", 1000), dimension=8, combiner='mean')]}
    return efl.Sample(features, columns);

def model_fn(model, sample):
  input = tf.concat([sample['deep'], sample['emb']], axis=1)
  fc1 = tf.layers.dense(input, 128, 
    kernel_initializer=tf.truncated_normal_initializer(
      stddev=0.001, dtype=tf.float32))
  fc2 = tf.layers.dense(
    fc1, 64, kernel_initializer=tf.truncated_normal_initializer(
      stddev=0.001, dtype=tf.float32))
  fc3 = tf.layers.dense(
    fc2, 32, kernel_initializer=tf.truncated_normal_initializer(
      stddev=0.001, dtype=tf.float32))
  y = tf.layers.dense(
    fc3, 1, kernel_initializer=tf.truncated_normal_initializer(
      stddev=0.001, dtype=tf.float32))
  loss = tf.losses.sigmoid_cross_entropy(sample['label'], y)
  return loss

CTR = efl.Model()
CTR.input_fn(input_fn)
CTR.loss_fn(model_fn)
CTR.optimizer_fn(efl.optimizer_fn.optimizer_setter(tf.train.GradientDescentOptimizer(0.01)))
CTR.compile()
CTR.fit(efl.procedure_fn.train(max_step=100), 
        log_step=10, 
        project_name="train")
