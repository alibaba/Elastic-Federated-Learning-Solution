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
import collections

from tensorflow.python.feature_column import feature_column_v2 as feature_column
from tensorflow.python.feature_column import dense_features
from tensorflow.python.framework import ops
from tensorflow.python.ops import variable_scope
from tensorflow.python.ops import array_ops

from efl import exporter
from efl.framework import task_scope
from efl.utils import config

class DenseFeatures(dense_features.DenseFeatures):
  def __init__(self, feature_columns, trainable=True, name=None, **kwargs):
    super(DenseFeatures, self).__init__(
        feature_columns=feature_columns,
        trainable=trainable,
        name=name,
        **kwargs)

  def build(self, _):
    for column in self._feature_columns:
      with variable_scope._pure_variable_scope(column.name):  # pylint: disable=protected-access
        column.create_state(self._state_manager)
    self.built = True

def get_feature_key(column):
  if isinstance(column, (feature_column.NumericColumn,
                         feature_column.HashedCategoricalColumn,
                         feature_column.VocabularyFileCategoricalColumn,
                         feature_column.VocabularyListCategoricalColumn,
                         feature_column.IdentityCategoricalColumn,
                         feature_column.SequenceCategoricalColumn)):
    return column.name
  elif isinstance(column, (feature_column.BucketizedColumn)):
    return get_feature_key(column.source_column)
  elif isinstance(column, (feature_column.WeightedCategoricalColumn,
                           feature_column.EmbeddingColumn,
                           feature_column.IndicatorColumn,
                           feature_column.SequenceCategoricalColumn)):
    return get_feature_key(column.categorical_column)
  elif isinstance(column, feature_column.CrossedColumn):
    return column.keys[0]
  else:
    raise ValueError('unsuppoted column:{}'.format(str(column)))

@exporter.export("make_parse_example_spec")
def make_parse_example_spec(feature_columns):
  result = {}
  for column in feature_columns:
    config = column._parse_example_spec
    for key, value in six.iteritems(config):
      if key in result and value != result[key]:
        raise ValueError(
            'feature_columns contain different parse_spec for key '
            '{}. Given {} and {}'.format(key, value, result[key]))
    result.update(config)
  return result

def input_layer(
    features,
    feature_columns,
    trainable=True):
  """See input_layer. `scope` is a name or variable scope to use."""
  feature_columns, column_index = _normalize_feature_columns(feature_columns)
  for column in feature_columns:
    if not isinstance(column, feature_column.DenseColumn):
      raise ValueError(
        'Items of feature_columns must be a _DenseColumn. '
        'You can wrap a categorical column with an '
        'embedding_column or indicator_column. Given: {}'.format(column))
  df = DenseFeatures(feature_columns, trainable=trainable)
  output_dict = {}
  concat_output = df(features, cols_to_output_tensors=output_dict)
  return concat_output, output_dict


def _normalize_feature_columns(feature_columns):
  """Normalizes the `feature_columns` input.

  This method converts the `feature_columns` to list type as best as it can. In
  addition, verifies the type and other parts of feature_columns, required by
  downstream library.

  Args:
    feature_columns: The raw feature columns, usually passed by users.

  Returns:
    The normalized feature column list.

  Raises:
    ValueError: for any invalid inputs, such as empty, duplicated names, etc.
  """
  if isinstance(feature_columns, feature_column.FeatureColumn):
    feature_columns = [feature_columns]

  if isinstance(feature_columns, collections.Iterator):
    feature_columns = list(feature_columns)

  if isinstance(feature_columns, dict):
    raise ValueError('Expected feature_columns to be iterable, found dict.')

  for column in feature_columns:
    if not isinstance(column, feature_column.FeatureColumn):
      raise ValueError('Items of feature_columns must be a FeatureColumn. '
                       'Given (type {}): {}.'.format(type(column), column))
  if not feature_columns:
    raise ValueError('feature_columns must not be empty.')
  name_to_idx = dict()
  output_columns = []
  index = []
  idx = 0
  for column in feature_columns:
    if column.name not in name_to_idx:
      name_to_idx[column.name] = idx
      output_columns.append(column)
      idx += 1
    index.append(name_to_idx[column.name])

  return output_columns, index
