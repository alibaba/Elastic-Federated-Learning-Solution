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

import tensorflow.compat.v1 as tf
import efl

def input_fn(model, mode):
  if mode == efl.MODE.TRAIN:
    dataio = efl.data.FederalDataIO("./follower_train", 256, model.communicator, model.federal_role, 0, 1, data_mode='local', num_epochs=10)
    dataio.fixedlen_feature('sample_id', 1, dtype=tf.int64)
    dataio.fixedlen_feature('feature', 14*28, dtype=tf.float32)
    dataio.fixedlen_feature('label', 1, dtype=tf.float32)
    features = dataio.read()
    model.add_hooks([dataio.get_hook()])
    columns = {
      "label": [tf.feature_column.numeric_column('label', 1)],
      "emb": [tf.feature_column.numeric_column('feature', 28*14)]}
    return efl.FederalSample(features, columns, model.federal_role, model.communicator, sample_id_name='sample_id')

def model_fn(model, sample):
  inputs = sample['emb']
  inputs = tf.reshape(inputs, [-1, 28, 14])
  right = efl.secret_sharing.share(inputs, model.communicator, 'share_right')
  left = model.recv('share_left', require_grad=False, shape=[-1, 28, 14])
  inputs = tf.reshape(tf.concat([left, right], axis=1), [-1, 28 * 28])
  y = efl.secret_sharing.dense(inputs, model.communicator, 'dense1', 128)
  y = efl.secret_sharing.dense(y, model.communicator, 'dense2', 10)
  y = efl.secret_sharing.reveal(y, model.communicator, 'reveal', efl.privacy.Role.SENDER)
  return y

DNN = efl.FederalModel()
DNN.input_fn(input_fn)
DNN.loss_fn(model_fn)
DNN.optimizer_fn(efl.optimizer_fn.optimizer_setter(tf.train.GradientDescentOptimizer(0.001)))
DNN.compile()
DNN.fit(efl.procedure_fn.train(),
        log_step=100,
        project_name="train")
