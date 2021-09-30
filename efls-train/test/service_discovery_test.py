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

import sys
sys.path.insert(0, '.')

import unittest
import threading
import json

from efl.service_discovery import service_discovery

class ServiceDiscoverySingleModeTest(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    pass

  @classmethod
  def tearDownClass(cls):
    pass

  def test_single_mode(self):
    jobs = ["scheduler", "ps", "worker"]
    ths = []
    for i in range(len(jobs)):
      ths.append(threading.Thread(
          target = service_discovery.start_service_discovery,
          args=("/tmp/scheduler_addr_3.txt", 1, 1, jobs[i], 0, False, True)))
      ths[-1].start()
    for th in ths:
      th.join()
      
    for i in range(len(jobs)):
      config = json.loads(service_discovery.generate_tf_config_and_set_env(
          jobs[i], 0))
      job = jobs[i]
      if job == "worker":
        self.assertEqual(config["task"]["index"], 0)
        self.assertEqual(config["task"]["type"], "worker")
      else:
        self.assertEqual(config["task"]["index"], 0)
        self.assertEqual(config["task"]["type"], job)        
      self.assertEqual(len(config["cluster"]["ps"]), 1)
      self.assertEqual(len(config["cluster"]["worker"]), 1)
    
if __name__ == '__main__':  
    unittest.main()
