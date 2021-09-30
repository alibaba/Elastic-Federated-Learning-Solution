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

import collections
from efl import exporter

class StageCombiner(object):
  def __init__(self, val):
    self.val = val

@exporter.export("stage_combiner.First")
class First(StageCombiner):
  "this StageCombiner returns first return value in all workers"
  @staticmethod
  def Combine(vals, orders):
    return vals[orders[0]]

@exporter.export("stage_combiner.Last")
class Last(StageCombiner):
  "this StageCombiner returns last return value in all workers"
  @staticmethod
  def Combine(vals, orders):
    return vals[orders[-1]]

@exporter.export("stage_combiner.Chief")
class Chief(StageCombiner):
  "this StageCombiner returns value in worker0"
  @staticmethod
  def Combine(vals, orders):
    return vals[0]

@exporter.export("stage_combiner.Mean")
class Mean(StageCombiner):
  "this StageCombiner returns all value's mean in all workers"
  @staticmethod
  def Combine(vals, orders):
    return sum(vals) / len(vals)

@exporter.export("stage_combiner.Sum")
class Sum(StageCombiner):
  "this StageCombiner returns all value's sum in all workers"
  @staticmethod
  def Combine(vals, orders):
    return sum(vals)

@exporter.export("stage_combiner.List")
class List(StageCombiner):
  "this StageCombiner returns value list in all workers"
  @staticmethod
  def Combine(vals, orders):
    return vals

def combine(lst, orders):
  return _combine_impl(lst, orders, lst)

def _combine_impl(lst, orders, xlst):
  cls = type(lst[0])
  for item in lst:
    if type(item) != cls:
      raise ValueError("type mismatch", lst, xlst)

  if cls == list:
    return _combine_list(lst, orders, xlst)
  elif cls == tuple:
    return _combine_tuple(lst, orders, xlst)
  elif cls == dict:
    return _combine_dict(lst, orders, xlst)
  elif issubclass(cls, StageCombiner):
    return _combine_combiner(lst, orders, xlst)
  elif cls == type(None):
    return None
  else:
    raise ValueError("cannot combine this type.", cls, lst, xlst)

def _combine_list(lst, orders, xlst):
  l = len(lst[0])
  for item in lst:
    if len(item) != l:
      raise ValueError("connot combine list, list length mismatch.", lst, xlst)
  rst = []
  for i in range(len(l)):
    rst.append(_combine_impl([item[i] for item in lst], orders, xlst))
  return rst

def _combine_tuple(lst, orders, xlst):
  l = len(lst[0])
  for item in lst:
    if len(item) != l:
      raise ValueError("connot combine tuple, tuple length mismatch.", lst, xlst)
  rst = []
  for i in range(len(l)):
    rst.append(_combine_impl([item[i] for item in lst], orders, xlst))
  return tuple(rst)

def _combine_dict(lst, orders, xlst):
  s = set(lst[0].keys())
  for item in lst:
    if set(lst[0].keys()) != s:
      raise ValueError("connot combine dict, dict keys mismatch.", lst, xlst)
  rst = {}
  for i in s:
    rst[i] = _combine_impl([lst[i] for j in lst], orders, xlst)
  return tuple(rst)

def _combine_combiner(lst, orders, xlst):
  cls = type(lst[0])
  return cls.Combine([item.val for item in lst], orders)
