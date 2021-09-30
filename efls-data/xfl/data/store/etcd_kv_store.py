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

from abc import ABCMeta

import etcd3

from xfl.data.store.sample_kv_store import SampleKvStore


class EtcdSampleKvStore(SampleKvStore, metaclass=ABCMeta):
  def __init__(self, client: etcd3.Etcd3Client, prefix: str) -> None:
    self._cli = client
    self._prefix = prefix

  def _get_key(self, id):
    return self._prefix + b'/' + id

  def exists(self, ids: list) -> list:
    return [len(list(self._cli.get_prefix(self._get_key(i), keys_only=True))) > 0 for i in ids]

  def keys(self) -> list:
    return [i[1].key[len(self._prefix) + 1:] for i in self._cli.get_prefix(self._prefix, keys_only=True)]

  def get(self, key):
    return self._cli.get(self._get_key(key))[0]

  def put(self, key, value) -> bool:
    self._cli.put(self._get_key(key), value)

  def size(self) -> int:
    return len(self.keys())
