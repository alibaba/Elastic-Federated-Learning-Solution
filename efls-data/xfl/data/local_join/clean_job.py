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


import argparse, redis
from xfl.common.logger import log

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='feature-inc task job cleaner')
  parser.add_argument('-n', '--job_name', type=str,
                      help='job name', required=True)
  parser.add_argument('--host_name', type=str,
                      help='redis host name', default='redis')

  args = parser.parse_args()
  conn = redis.StrictRedis(host=args.host_name)
  keys = conn.keys("{}*".format(args.job_name))
  if not keys:
    log.info("There is no key related with job {} should been deleted.".format(args.job_name))
  else:
    conn.delete(*keys)
    log.info("{} keys related with job {} have been deleted.".format(len(keys), args.job_name))
