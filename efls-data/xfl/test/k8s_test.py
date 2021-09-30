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

import unittest
from xfl.k8s.k8s_client import K8sClient
from xfl.k8s import k8s_resource
import os


class TestK8sClinet(unittest.TestCase):
  def setUp(self) -> None:
    self._client = K8sClient()
    if os.environ['K8S_CONFIG'] is not None and len(os.environ['K8S_CONFIG']) > 0:
      self._client.init(os.environ['K8S_CONFIG'])
    else:
      self._client.init(os.path.join(os.environ['HOME'], '.kube', 'config'))
    self.app_name = "testapp"
    self.bucket_id = 0
    self.target_port = 50051
    self.service_name = k8s_resource.get_service_name(self.app_name, self.bucket_id)
    self.ingress_name = k8s_resource.get_ingress_name(self.service_name)

  def tearDown(self) -> None:
    self._client.close()

  def testIngress(self):
    k8s_resource.create_data_join_service(self._client, self.app_name, self.bucket_id, self.target_port)
    svc = self._client.get_service(self.service_name)
    self.assertIsNotNone(svc)
    k8s_resource.release_data_join_service(self._client, self.app_name, self.bucket_id)

    k8s_resource.create_data_join_ingress(self._client, self.app_name, self.bucket_id)
    ing = self._client.get_ingress(self.ingress_name)
    self.assertIsNotNone(ing)
    k8s_resource.release_data_join_ingress(self._client, self.app_name, self.bucket_id)


if __name__ == '__main__':
  unittest.main(verbosity=1)
