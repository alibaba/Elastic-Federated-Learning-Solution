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

import threading
from efl import exporter

local = threading.local()

@exporter.export("Stage")
class Stage(object):
  def __init__(self):
    pass

  @property
  def sess(self):
    return local.sess

  def __call__(self, *args, **kwargs):
    def func(sess):
      local.sess = sess
      return self.run(*args, **kwargs)
    return func

  def run(self, *args, **kwargs):
    raise NotImplementedError("Stage's run func should be implemented")
