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

from concurrent.futures import _base


class _WorkItem(object):
  def __init__(self, future, fn, args, kwargs):
    self.future = future
    self.fn = fn
    self.args = args
    self.kwargs = kwargs

  def run(self):
    if not self.future.set_running_or_notify_cancel():
      return

    try:
      result = self.fn(*self.args, **self.kwargs)
    except BaseException as exc:
      self.future.set_exception(exc)
      # Break a reference cycle with the exception 'exc'
      self = None
    else:
      self.future.set_result(result)


class DirectThreadPoolExecutor(_base.Executor):
  def __init__(self) -> None:
    pass

  def submit(*args, **kwargs):
    if len(args) >= 2:
      self, fn, *args = args
    elif not args:
      raise TypeError("descriptor 'submit' of 'ThreadPoolExecutor' object "
                      "needs an argument")
    elif 'fn' in kwargs:
      fn = kwargs.pop('fn')
      self, *args = args
      import warnings
      warnings.warn("Passing 'fn' as keyword argument is deprecated",
                    DeprecationWarning, stacklevel=2)
    else:
      raise TypeError('submit expected at least 1 positional argument, '
                      'got %d' % (len(args) - 1))

      f = _base.Future()
      w = _WorkItem(f, fn, args, kwargs)
      w.run()
      return f

  def shutdown(self, wait=True):
    pass
