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

import os
from tensorflow.python.platform import gfile


def assert_valid_dir(path):
  if not gfile.Exists(path):
    raise RuntimeError("path {} not exist.".format(path))
  if not gfile.IsDirectory(path):
    raise RuntimeError("path {} is not a directory!".format(path))


def list_data_file_recursively(path):
  res = []
  for tuple in gfile.Walk(path):
    for f in tuple[2]:
      if str(f).startswith("_") or str(f).startswith("."):
        continue
      res.append(os.path.join(tuple[0], f))
  return res
