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

from xfl.common.logger import log
from functools import wraps
from traceback import format_exc
import time

def retry_fn(retry_times: int = 3, needed_exceptions=None, retry_interval: int = 0.2):
  def decorator_retry_fn(f):
    nonlocal needed_exceptions
    if needed_exceptions is None:
      needed_exceptions = [Exception]

    @wraps(f)
    def wrapper(*args, **kwargs):
      for i in range(retry_times):
        try:
          return f(*args, **kwargs)
        except tuple(needed_exceptions):
          log.error('Call function failed, retrying %s times...',
                    i + 1)
          time.sleep(retry_interval)
          log.error('Exceptions:\n%s', format_exc())
          log.error(
            'function name is %s, args are %s, kwargs are %s',
            f.__name__, repr(args), repr(kwargs))
          if i == retry_times - 1:
            raise
          continue

    return wrapper

  return decorator_retry_fn
