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

import json
import os
import sys

from tensorflow.python.ops import array_ops
from tensorflow.python.data.experimental.ops import optimization
from tensorflow.python.data.ops import dataset_ops
from tensorflow.python.data.util import convert
from tensorflow.python.data.util import nest
from tensorflow.python.framework import constant_op
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import errors
from tensorflow.python.framework import ops
from tensorflow.python.framework import tensor_shape
from tensorflow.python.framework import tensor_spec

from efl import lib
from efl import exporter

@exporter.export("data.FederalDataset")
class FederalDataset(dataset_ops.DatasetV2):
  """A `Dataset` comprising records from one or more table files."""

  def __init__(self,
               filenames,
               block_ids=None,
               sample_index=0,
               compression_type='',
               buffer_size=256 * 1024):
    """Creates FederalDataset`.

    Args:
     filenames: A tf.data.Dataset` containing one or
       more filenames.
     compression_type: (Optional.) A `tf.string` scalar evaluating to one of
       `""` (no compression), `"ZLIB"`, or `"GZIP"`.
     buffer_size: (Optional.) A `tf.int64` scalar representing the number of
       bytes in the read buffer. 0 means no buffering.
    """
    self._filenames = filenames
    if block_ids is None:
      block_ids = filenames
    self._block_ids = block_ids
    self._sample_index = sample_index
    self._compression_type = compression_type
    self._buffer_size = buffer_size
    self._variant_tensor_attr = self._as_variant_tensor()
    self._graph_attr = ops.get_default_graph()

  def _as_variant_tensor(self):
    return lib.ops.federal_dataset(
        self._filenames,
        self._block_ids,
        self._sample_index,
        self._compression_type,
        self._buffer_size)

  def _inputs(self):
    return []

  @property
  def element_spec(self):
    return tensor_spec.TensorSpec([], dtypes.string)
