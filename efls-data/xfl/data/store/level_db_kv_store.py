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
import plyvel
from abc import ABCMeta
from xfl.data.store.sample_kv_store import SampleKvStore

class LevelDbKvStore(SampleKvStore, metaclass=ABCMeta):
  def __init__(self, path,
          write_buffer_size=128*1024*1024,
          max_open_files=1000,
          max_file_size=32*1024*1024) -> None:
    super().__init__()
    self._path = path
    self._db = plyvel.DB(name=path,
            create_if_missing=True,
            error_if_exists=True,
            write_buffer_size=write_buffer_size,
            max_open_files=max_open_files,
            max_file_size=max_file_size)

  def put(self, key, value) -> bool:
    res = True
    self._db.put(key, value)
    return res

  def exists(self, ids: list) -> list:
    return [self._db.get(i) is not None for i in ids]

  def get(self, key):
    return self._db.get(key)

  def keys(self) -> list:
    res = []
    with self._db.iterator() as it:
      for k, v in it:
        res.append(k)
    return res

  def size(self) -> int:
    return len(self.keys())

  def clear(self):
    self._db.close()
    plyvel.destroy_db(self._path)

  def __iter__(self):
    self._it = self._db.iterator()
    return self

  def __next__(self):
    return next(self._it)[0]
