# Copyright 2018, The TensorFlow Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Change made to the origin file:
# - Motify the logic of DPOptimizerClass's compute_gradients
#
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

import tensorflow.compat.v1 as tf

from tensorflow_privacy.privacy.analysis import privacy_ledger
from tensorflow_privacy.privacy.dp_query import gaussian_query

from efl import exporter

def zeros_like(arg):
  try:
    arg = tf.convert_to_tensor(value=arg)
  except TypeError:
    pass
  return tf.zeros(tf.shape(arg), arg.dtype)

def initial_sample_state(self, template):
  return tf.nest.map_structure(zeros_like, template)

gaussian_query.GaussianSumQuery.initial_sample_state = initial_sample_state

_DEFAULT_OPT_CONFIG = {
  'REDUCE': 'mean'
}

@exporter.export('make_optimizer_class')
def make_optimizer_class(cls):
  """Constructs a DP optimizer class from an existing one."""
  parent_code = tf.train.Optimizer.compute_gradients.__code__
  child_code = cls.compute_gradients.__code__
  GATE_OP = tf.train.Optimizer.GATE_OP
  if child_code is not parent_code:
    tf.logging.warn(
        'WARNING: Calling make_optimizer_class() on class %s that overrides '
        'method compute_gradients(). Check to ensure that '
        'make_optimizer_class() does not interfere with overridden version.',
        cls.__name__)

  class DPOptimizerClass(cls):
    """Differentially private subclass of given class cls."""

    def __init__(
        self,
        dp_sum_query,
        num_microbatches=None,
        unroll_microbatches=False,
        *args,
        **kwargs):
      """Initialize the DPOptimizerClass.
      Args:
        dp_sum_query: DPQuery object, specifying differential privacy
          mechanism to use.
        num_microbatches: How many microbatches into which the minibatch is
          split. If None, will default to the size of the minibatch, and
          per-example gradients will be computed.
        unroll_microbatches: If true, processes microbatches within a Python
          loop instead of a tf.while_loop. Can be used if using a tf.while_loop
          raises an exception.
      """
      super(DPOptimizerClass, self).__init__(*args, **kwargs)
      self._dp_sum_query = dp_sum_query
      self._num_microbatches = num_microbatches
      self._global_state = self._dp_sum_query.initial_global_state()
      # Beware: When num_microbatches is large (>100), enabling this parameter
      # may cause an OOM error. Set unroll_microbatches=True to avoid this bug.
      self._unroll_microbatches = unroll_microbatches
      self._was_compute_gradients_called = False

    def compute_gradients(self,
                          loss,
                          var_list,
                          gate_gradients=GATE_OP,
                          aggregation_method=None,
                          colocate_gradients_with_ops=False,
                          grad_loss=None,
                          gradient_tape=None,
                          opt_config=_DEFAULT_OPT_CONFIG):
      self._was_compute_gradients_called = True
      if callable(loss):
        # TF is running in Eager mode, check we received a vanilla tape.
        if not gradient_tape:
          raise ValueError('When in Eager mode, a tape needs to be passed.')
        raise NotImplementedError('Eager mode is not available yet')
      else:
        # TF is running in graph mode, check we did not receive a gradient tape.
        if gradient_tape:
          raise ValueError('When in graph mode, a tape should not be passed.')

        # Note: it would be closer to the correct i.i.d. sampling of records if
        # we sampled each microbatch from the appropriate binomial distribution,
        # although that still wouldn't be quite correct because it would be
        # sampling from the dataset without replacement.
        if self._num_microbatches is None:
          self._num_microbatches = tf.shape(loss)[0]
        batch_size = tf.shape(loss)[0]
        num_microbatches = tf.cond(tf.equal(batch_size % self._num_microbatches, 0),
                                   lambda: self._num_microbatches,
                                   lambda: batch_size)
        microbatch_size = batch_size // num_microbatches

        loss = tf.reshape(loss, [num_microbatches, -1])
        grad_loss = None if grad_loss is None else tf.reshape(grad_loss, [num_microbatches, -1])
        sample_params = (
            self._dp_sum_query.derive_sample_params(self._global_state))

        reduce_func = opt_config.pop('REDUCE', 'mean')
        if reduce_func == 'mean':
          reduce_func = tf.reduce_mean
        elif reduce_func == 'sum':
          reduce_func = tf.reduce_sum
        elif not callable(reduce_func):
          raise ValueError('No such reduce function called \'{}\'.'.format(str(reduce_func)))


        def process_microbatch(i, sample_state):
          """Process one microbatch (record) with privacy helper."""
          reduce_loss = reduce_func(tf.gather(loss, [i]), axis=0)
          reduce_grad_loss = None if grad_loss is None else reduce_func(tf.gather(grad_loss, [i]), axis=0)
          grads, _ = zip(*super(DPOptimizerClass, self).compute_gradients(
              reduce_loss, var_list, gate_gradients, aggregation_method,
              colocate_gradients_with_ops, reduce_grad_loss))
          grads_list = [
              g if g is not None else tf.zeros_like(v)
              for (g, v) in zip(list(grads), var_list)
          ]
          sample_state = self._dp_sum_query.accumulate_record(
              sample_params, sample_state, grads_list)
          return sample_state


        if var_list is None:
          var_list = (
              tf.trainable_variables() + tf.get_collection(
                  tf.GraphKeys.TRAINABLE_RESOURCE_VARIABLES))

        sample_state = self._dp_sum_query.initial_sample_state(var_list)

        if self._unroll_microbatches:
          for idx in range(num_microbatches):
            sample_state = process_microbatch(idx, sample_state)
        else:
          # Use of while_loop here requires that sample_state be a nested
          # structure of tensors. In general, we would prefer to allow it to be
          # an arbitrary opaque type.
          cond_fn = lambda i, _: tf.less(i, num_microbatches)
          body_fn = lambda i, state: [tf.add(i, 1), process_microbatch(i, state)]
          idx = tf.constant(0)
          _, sample_state = tf.while_loop(
              cond=cond_fn, body=body_fn, loop_vars=[idx, sample_state])

        grad_sums, self._global_state = (
            self._dp_sum_query.get_noised_result(
                sample_state, self._global_state))

        def safe_normalize(v):
          try:
            return tf.truediv(v, tf.cast(num_microbatches, tf.float32))
          except TypeError:
            return None

        final_grads = tf.nest.map_structure(safe_normalize, grad_sums)

        return list(zip(final_grads, var_list))

  return DPOptimizerClass


@exporter.export('make_gaussian_optimizer_class')
def make_gaussian_optimizer_class(cls):
  """Constructs a DP optimizer with Gaussian averaging of updates."""

  class DPGaussianOptimizerClass(make_optimizer_class(cls)):
    """DP subclass of given class cls using Gaussian averaging."""

    def __init__(
        self,
        l2_norm_clip,
        noise_multiplier,
        num_microbatches=None,
        ledger=None,
        unroll_microbatches=False,
        *args,
        **kwargs):
      dp_sum_query = gaussian_query.GaussianSumQuery(
          l2_norm_clip, l2_norm_clip * noise_multiplier)

      if ledger:
        dp_sum_query = privacy_ledger.QueryWithLedger(dp_sum_query,
                                                      ledger=ledger)

      super(DPGaussianOptimizerClass, self).__init__(
          dp_sum_query,
          num_microbatches,
          unroll_microbatches,
          *args,
          **kwargs)

    @property
    def ledger(self):
      return self._dp_sum_query.ledger

  return DPGaussianOptimizerClass

AdagradOptimizer = tf.train.AdagradOptimizer
AdamOptimizer = tf.train.AdamOptimizer
GradientDescentOptimizer = tf.train.GradientDescentOptimizer

@exporter.export('DPAdagradOptimizer')
class DPAdagradOptimizer(make_optimizer_class(AdagradOptimizer)):
  pass

@exporter.export('DPAdamOptimizer')
class DPAdamOptimizer(make_optimizer_class(AdamOptimizer)):
  pass

@exporter.export('DPGradientDescentOptimizer')
class DPGradientDescentOptimizer(make_optimizer_class(GradientDescentOptimizer)):
  pass

@exporter.export('DPAdagradGaussianOptimizer')
class DPAdagradGaussianOptimizer(make_gaussian_optimizer_class(AdagradOptimizer)):
  pass

@exporter.export('DPAdamGaussianOptimizer')
class DPAdamGaussianOptimizer(make_gaussian_optimizer_class(AdamOptimizer)):
  pass

@exporter.export('DPGradientDescentGaussianOptimizer')
class DPGradientDescentGaussianOptimizer(make_gaussian_optimizer_class(GradientDescentOptimizer)):
  pass

