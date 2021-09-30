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

import logging
import sys
import numpy as np
from tensorflow.python.platform import tf_logging

class LogStderrFilter(logging.Filter):
  def filter(self, rec):
    return rec.levelno in (logging.FATAL, logging.ERROR, logging.WARNING)

class LogStdoutFilter(logging.Filter):
  def filter(self, rec):
    return rec.levelno in (logging.DEBUG, logging.INFO)

def redirect_log():
  np.set_printoptions(threshold=np.inf)
  formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
  logger = tf_logging.get_logger()
  pre_handlers = logger.handlers
  for handler in pre_handlers:
    logger.removeHandler(handler)
  h1 = logging.StreamHandler(sys.stdout)
  h1.setLevel(logging.INFO)
  h1.setFormatter(formatter)
  h1.addFilter(LogStdoutFilter())
  logger.addHandler(h1)
  h2 = logging.StreamHandler(sys.stderr)
  h2.setLevel(logging.WARNING)
  h2.setFormatter(formatter)
  h2.addFilter(LogStderrFilter())
  logger.addHandler(h2)
  tf_logging.set_verbosity(tf_logging.INFO)
  tf_logging.get_logger().propagate = False
