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

import six

import tensorflow as tf
from tensorflow.python.platform import tf_logging
from tensorflow.python.framework import ops
from tensorflow.python.framework import dtypes
from tensorflow.python.ops import math_ops
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import check_ops
from tensorflow.python.ops import gen_control_flow_ops
from tensorflow.python.feature_column import feature_column_v2 as feature_column

from efl import exporter
from efl.utils import column_util

@exporter.export('Sample')
class Sample(object):
  r'''efl sample returned by input_fn'''
  def __init__(self, features, columns):  
    self._features = features
    if not isinstance(columns, dict):
      raise ValueError("columns must be a dict")
    self._columns = columns
    self._transformed_feature_groups = {}
    self._transform()

  def to_dict(self):
    return self._transformed_feature_groups

  def create(self, fgrps):
    sample = copy.copy(self)
    sample._transformed_feature_groups = fgrps
    return sample

  def set_transformed_feature_groups(self, fgrps):
    self._transformed_feature_groups = fgrps

  @property
  def features(self):
    return self._features

  def __getitem__(self, name):
    r'''get transformed features'''
    if len(self._transformed_feature_groups) == 0:
      raise RuntimeError('transform should be called before call feature')
    if name not in self._transformed_feature_groups:
      raise RuntimeError('no feature group[{}] found in transform features[{}]'.format(
          name, self._transformed_feature_groups.keys()))
    return self._transformed_feature_groups[name]

  def __setitem__(self, key, value):
    self._transformed_feature_groups[key] = value

  def __delitem__(self, key):
    if key not in self._transformed_feature_groups:
      raise RuntimeError("sample don't have feature[{}]".format(key))
    del self._transformed_feature_groups[key]

  def __contains__(self, key):
    return key in self._transformed_feature_groups

  def __iter__(self):
    return iter(self._transformed_feature_groups)

  def items(self):
    return self._transformed_feature_groups.items()

  def __len__(self):
    return len(self._transformed_feature_groups)

  def before_step_ops(self):
    return [gen_control_flow_ops.no_op()]

  def _transform(self):
    r'''transform inputs to dense tensors by feature columns'''
    all_features = self._features
    for group, columns in self._columns.items():
      if group in self._transformed_feature_groups:
        raise RuntimeError("feature group[{}] has been transformed".format(group))
      emb = self._input_from_feature_columns(all_features, columns)
      self._transformed_feature_groups[group] = emb
    return self

  def _input_from_feature_columns(self, features, columns, **kwargs):
    concat_output, output_dcit = column_util.input_layer(features, columns, **kwargs)
    return concat_output


@exporter.export('FederalSample')
class FederalSample(Sample):
  r'''efl sample returned by input_fn'''
  def __init__(self, features, columns,
               federal_role, communicator,
               sample_id_name=None,
               verify_id=True,
               name='sample'):
    if sample_id_name is None:
      tf_logging.info("FederalSample running without check sample_ids.")
    else:
      if sample_id_name not in features:
        raise ValueError('sample_id_name not in features, given: {}'.format(sample_id_name))
      if federal_role not in ('leader', 'follower'):
        raise ValueError('federal_role must be set one of [leader/follower] in FederalSample')
      if communicator is None:
        raise ValueError('communicator must set in FederalSample')
    self._federal_role = federal_role
    self._communicator = communicator
    self._sample_id_name = sample_id_name
    self._verify_id = verify_id
    self._name = name
    super(FederalSample, self).__init__(features,
                                        columns)

  def verify_sample_id(self):
    if (self._sample_id_name is None) or (not self._verify_id):
      verify_op = gen_control_flow_ops.no_op()
    elif self._federal_role == 'leader':
      sample_id = self._features[self._sample_id_name]
      if not sample_id.dtype == tf.string:
        sample_id = tf.strings.as_string(sample_id)
      sample_id = tf.strings.to_hash_bucket_fast(sample_id, 2**31 - 1)
      verify_op = self._communicator.send(
          '_verify_sample_ids_' + self._name , sample_id)
    else:
      sample_id = self._features[self._sample_id_name]
      if not sample_id.dtype == tf.string:
        sample_id = tf.strings.as_string(sample_id)
      sample_id = tf.strings.to_hash_bucket_fast(sample_id, 2**31 - 1)
      with ops.control_dependencies([sample_id]):
        recv_sample_ids = self._communicator.recv('_verify_sample_ids_' + self._name , dtype=sample_id.dtype)
        verify_op = check_ops.assert_equal(recv_sample_ids, sample_id)
    return verify_op

  def before_step_ops(self):
    return [self.verify_sample_id()]
