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
from xfl.data.redis.rediswq import RedisWQ
from xfl.common.logger import log
from xfl.data.redis.redis_lock import RedisLock
import time

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='local join worker start command')
  parser.add_argument('-n', '--job_name', type=str,
                      help='job name', required=True)

  parser.add_argument('-i', '--input_dir', type=str,
                      help='the input_dir of local join, should be a dir, eg `file:///home/xxx` or `oss://bucket/file`',
                      required=True)

  parser.add_argument('-o', '--output_dir', type=str,
                      help='the output_dir of local join, should be a dir, eg `file:///home/xxx` or `oss://bucket/file`',
                      required=True)

  parser.add_argument('--split_num', type=int,
                      default=1,
                      required=True)

  parser.add_argument('--timeout_s', type=int,
                      default=300,
                      required=False)

  parser.add_argument('--left_key', action='append')
  parser.add_argument('--right_key', action='append')
  parser.add_argument('--aux_table', action='append')

  args = parser.parse_args()

  assert len(args.left_key) == len(args.right_key) == len(args.aux_table)


  #init wq
  work_queue = RedisWQ(name=args.job_name, host='redis')
  lock = RedisLock(args.job_name + "_job_lock")
  token = lock.acquire(blocking=True, blocking_timeout=60)
  if token:
    if work_queue.empty():
      log.info("Begin to init work queue with size {}".format(args.split_num))
      work_queue.add_item(*[str(i) for i in range(args.split_num)])
    else:
      log.info("Work queue has been inited, continue working")
    lock.release()
  else:
    log.warning("Worker Queue inited with some errors.")
    raise RuntimeError("Worker Queue inited fail.")

  # fetch task idx from work queue
  log.info("Job {} begins to run, session id: {}.".format(args.job_name, work_queue.session_id()))
  aux_tables = [AuxTable(path=t, key_col=k) for k, t in zip(args.right_key, args.aux_table)]
  while not work_queue.empty():
    work_item = work_queue.lease(lease_secs=args.timeout_s, block=False, timeout=None)
    if work_item is not None:
      log.info("Begin to process task {}.".format(work_item))
      worker = LocalJoinWorker(input_dir=args.input_dir,
                               output_dir=args.output_dir,
                               worker_idx=int(work_item),
                               worker_num=args.split_num,
                               left_keys=args.left_key,
                               aux_tables=aux_tables
                               )
      worker.open()
      worker.run()
      work_queue.complete(item=work_item)
      log.info("Task {} finished. Try to fetch next task.".format(work_item))
    else:
      log.info("Waiting other processing workers finish..")
      time.sleep(5)

  if lock.acquire(blocking=False):
    log.info("Begin to clear WorkQueue..")
    work_queue.clear()
    lock.release()
  log.info("WorkQueue empty, exit successfully!")
