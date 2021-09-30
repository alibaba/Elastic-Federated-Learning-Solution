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
import time
import unittest
from unittest import TestCase

from xfl.k8s.k8s_client import K8sClient
from xfl.service.data_join_server import K8sResourceHandler


class TestK8sResourceHandler(TestCase):
  def setUp(self) -> None:
    self._client = K8sClient()
    if os.environ['K8S_CONFIG'] is not None and len(os.environ['K8S_CONFIG']) > 0:
      config_path = os.environ['K8S_CONFIG']
    else:
      config_path = os.path.join(os.environ['HOME'], '.kube', 'config')

    self.app_name = "testapp"
    self.bucket_id = 0
    self.target_port = 50051

    self.k8s_resource_handler = K8sResourceHandler(
      job_name=self.app_name,
      bucket_id=self.bucket_id,
      port=self.target_port,
      config_path=config_path
    )

  def testCreateAndDelete(self):
    self.k8s_resource_handler.create()
    print("create ok! wait 10s")
    time.sleep(60)
    self.k8s_resource_handler.delete()
    print("delete ok!")

if __name__ == '__main__':
  unittest.main(verbosity=1)
