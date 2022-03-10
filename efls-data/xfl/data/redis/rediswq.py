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
import uuid
import mmh3
from xfl.common.logger import log

class RedisWQ(object):
  """
     workqueue on redis.
     not thread-safe.
  """

  def __init__(self, name, **redis_kwargs):
    self._db = redis.StrictRedis(**redis_kwargs)
    self._session = str(uuid.uuid4())
    self._main_q_key = name
    self._processing_q_key = name + ":processing"
    self._lease_key_prefix = name + ":leased_by_session:"
    self._wq_lock_name = name + "_wq_lock"
    self._lock = self._db.lock(self._wq_lock_name, timeout=60, blocking_timeout=60)

  def session_id(self):
    return self._session

  def _main_qsize(self):
    return self._db.llen(self._main_q_key)

  def _processing_qsize(self):
    return self._db.llen(self._processing_q_key)

  def empty(self):
    """Return True if the queue is empty, including work being done, False otherwise.
       it should be noticed that 'False' may caused by some crashed or ongoing workers
       (i.e. _main_qsize()==0 but _processing_qsize > 0)
    """
    return self._main_qsize() == 0 and self._processing_qsize() == 0

  def check_expired_leases(self):
    processing_items = self._db.lrange(self._processing_q_key, 0, -1)
    for item in processing_items:
      if not self._lease_exists(item):
        if self._lock.acquire(blocking_timeout=60):
          log.warning("work_item {} lease expired. restart it!".format(item))
          self._db.lrem(self._processing_q_key, 0, item)
          self._db.lpushx(self._main_q_key, item)
          self._lock.release()

  def _itemkey(self, item):
    """Returns a string that uniquely identifies an item (bytes)."""
    return str(mmh3.hash(item))

  def _lease_exists(self, item):
    """True if a lease on 'item' exists."""
    return self._db.exists(self._lease_key_prefix + self._itemkey(item))

  def lease(self, lease_secs=60, block=True, timeout=None):
    if block:
      item = self._db.brpoplpush(self._main_q_key, self._processing_q_key, timeout=timeout)
    else:
      item = self._db.rpoplpush(self._main_q_key, self._processing_q_key)
    if item:
      # Record that we (this session id) are working on a key.  Expire that
      # note after the lease timeout.
      # Note: if we crash at this line of the program, then GC will see no lease
      # for this item a later return it to the main queue.
      itemkey = self._itemkey(item)
      self._db.setex(self._lease_key_prefix + itemkey, lease_secs, self._session)
    return item

  def complete(self, item):
    """Complete working on the item with 'value'.

    If the lease expired, the item may not have completed, and some
    other worker may have picked it up.  There is no indication
    of what happened.
    """
    self._db.lrem(self._processing_q_key, 0, item)
    # If we crash here, then the GC code will try to move the value, but it will
    # not be here, which is fine.  So this does not need to be a transaction.
    itemkey = self._itemkey(item)
    self._db.delete(self._lease_key_prefix + itemkey)

  def clear(self):
    """
      clean up all keys associated with "name".
    """
    processing_items = self._db.lrange(self._processing_q_key, 0, -1)
    for item in processing_items:
      itemkey = self._itemkey(item)
      self._db.delete(self._lease_key_prefix + itemkey)
    self._db.delete(self._processing_q_key)
    self._db.delete(self._main_q_key)

  def add_item(self, *item):
      self._db.lpush(self._main_q_key, *item)
