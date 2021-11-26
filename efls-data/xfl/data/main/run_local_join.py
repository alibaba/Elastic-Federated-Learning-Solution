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

import argparse
from xfl.data.local_join.worker import LocalJoinWorker
from xfl.data.local_join.aux_table import AuxTable
import os

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='local join worker start command')
  parser.add_argument('-i', '--input_dir', type=str,
                      help='the input_dir of local join, should be a dir, eg `file:///home/xxx` or `oss://bucket/file`',
                      required=True)

  parser.add_argument('-o', '--output_dir', type=str,
                      help='the output_dir of local join, should be a dir, eg `file:///home/xxx` or `oss://bucket/file`',
                      required=True)

  default_worker_idx = 0 if not os.environ['JOB_COMPLETION_INDEX'] else int(os.environ['JOB_COMPLETION_INDEX'])
  parser.add_argument('--worker_idx', type=int,
                      default=default_worker_idx
                      )

  parser.add_argument('--worker_num', type=int,
                      default=1,
                      required=True)

  parser.add_argument('--left_key', action='append')
  parser.add_argument('--right_key', action='append')
  parser.add_argument('--aux_table', action='append')

  args = parser.parse_args()

  assert len(args.left_key) == len(args.right_key) == len(args.aux_table)
  aux_tables = [AuxTable(path=t, key_col=k) for k, t in zip(args.right_key, args.aux_table)]
  worker = LocalJoinWorker(input_dir=args.input_dir,
                           output_dir=args.output_dir,
                           worker_idx=args.worker_idx,
                           worker_num=args.worker_num,
                           left_keys=args.left_key,
                           aux_tables=aux_tables
                           )
  worker.open()
  worker.run()