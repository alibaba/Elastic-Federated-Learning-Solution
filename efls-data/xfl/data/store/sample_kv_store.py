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

import abc
from abc import ABCMeta


class SampleKvStore(object):
  @abc.abstractmethod
  def exists(self, ids: list) -> list:
    """
    input is he list of ids, return a list of bools whose size is the same as input list.
    the returned list represent existence of each id.
    @param ids: list of id
    @return list of bool
    """
    ...

  @abc.abstractmethod
  def keys(self) -> list:
    """
    @return: list of ids
    """
    ...

  @abc.abstractmethod
  def get(self, key):
    """
    @param key:
    @return: value or None if not exist
    """
    ...

  @abc.abstractmethod
  def put(self, key, value) -> bool:
    """
    @param key:
    @param value:
    @return: if there exists the `key`, return false, otherwise true.
    """
    ...

  @abc.abstractmethod
  def size(self) -> int:
    ...

  @abc.abstractmethod
  def clear(self):
    ...

  @abc.abstractmethod
  def __iter__(self):
    ...

  @abc.abstractmethod
  def __next__(self):
    ...

class DictSampleKvStore(SampleKvStore, metaclass=ABCMeta):
  def __init__(self) -> None:
    super().__init__()
    self._store = {}

  def put(self, key, value) -> bool:
    self._store[key] = value
    return True

  def exists(self, ids: list) -> list:
    return [i in self._store for i in ids]

  def get(self, key):
    return self._store.get(key)

  def keys(self) -> list:
    return list(self._store.keys())

  def size(self) -> int:
    return len(self._store)

  def clear(self):
    self._store.clear()

  def __iter__(self):
    self._it = iter(self._store)
    return self

  def __next__(self):
    return next(self._it)
