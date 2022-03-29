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

import redis

class RedisLock(object):
  def __init__(self, name, conn=redis.StrictRedis(host='redis')):
    self._name = name
    self._lock = conn.lock(name=name)

  def acquire(self, blocking=None, blocking_timeout=None):
    return self._lock.acquire(blocking=blocking, blocking_timeout=blocking_timeout)

  def release(self):
    self._lock.release()