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

from tensorflow.python.ops import variable_scope as vs
from tensorflow.python.ops import metrics

from efl import exporter

@exporter.export('metrics.gauc')
def gauc(labels,
         predictions,
         indicators,
         metrics_collections=None,
         updates_collections=None,
         name=None):
  with vs.variable_scope(name, 'gauc', (labels, predictions, indicators)):
    aucs, counts = _ops.gauc_calc(labels, predictions, indicators)
    return metrics.mean(
        aucs, counts,
        metrics_collections=metrics_collections,
        updates_collections=updates_collections,
        name=name)

@exporter.export('metrics.auc')
def auc(labels,
        predictions,
        weights=None,
        num_thresholds=200,
        metrics_collections=None,
        updates_collections=None,
        curve='ROC',
        name=None,
        summation_method='trapezoidal'):
  return metrics.auc(labels,
                     predictions,
                     weights=weights,
                     num_thresholds=num_thresholds,
                     metrics_collections=metrics_collections,
                     updates_collections=updates_collections,
                     curve=curve,
                     name=name,
                     summation_method=summation_method)
