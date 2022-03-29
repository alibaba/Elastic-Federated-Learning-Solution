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


from typing import List
from xfl.data.local_join import utils


class FileSharding(object):
  def shard(self, worker_idx, worker_num, input_path, output_path) -> List[tuple]:
    shards_to_process = []
    utils.assert_valid_dir(input_path)
    input_files = utils.list_data_file_recursively(input_path)
    for i, f in enumerate(input_files):
      if i % worker_num == worker_idx:
        o_file_path = f.replace(input_path.rstrip("/"), output_path.rstrip("/"), 1)
        shards_to_process.append((f, o_file_path))
    return shards_to_process
