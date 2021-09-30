# Copyright 2021 Alibaba Group Holding Limited. All Rights Reserved.
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

import threading
from abc import ABCMeta

import cardinality
from pyflink.datastream.state import MapState

from xfl.common.logger import log
from xfl.data.store.sample_kv_store import SampleKvStore


class FlinkStateKvStore(SampleKvStore, metaclass=ABCMeta):
  def __init__(self, state: MapState):
    self._state_handler = {threading.current_thread().ident: state}

  def add_handler(self, thread_id, state):
    log.info("add handler thread_id {}, state id{}".format(thread_id, id(state)))
    self._state_handler[thread_id] = state

  def get_handler(self):
    return self._state_handler[threading.current_thread().ident]

  def exists(self, ids: list) -> list:
    log.info("get handler id {}".format(id(self.get_handler())))
    return [self.get_handler().contains(i) for i in ids]

  def keys(self) -> list:
    return list(self.get_handler().keys())

  def put(self, key, value) -> bool:
    res = not self.get_handler().contains(key)
    self.get_handler().put(key, value)
    return res

  def size(self) -> int:
    return cardinality.count(self.get_handler().keys())

  def get(self, key):
    return self.get_handler().get(key)
