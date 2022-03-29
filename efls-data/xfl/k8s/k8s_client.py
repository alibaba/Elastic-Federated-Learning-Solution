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

import kubernetes
from kubernetes import client
from kubernetes.client import ApiException

from xfl.common.logger import log
from http import HTTPStatus


class K8sClient(object):
  def __init__(self):
    self.core_api = None
    self.network_api = None
    self.app_api = None

    self.core_api = client.CoreV1Api()
    self.network_api = client.NetworkingV1Api()
    self.app_api = client.AppsV1Api()

  def init(self, config_path: str = None):

    if config_path is not None and len(config_path) > 0:
      log.info("init k8s client from path {}".format(config_path))
      kubernetes.config.load_kube_config(config_path)

    else:
      log.info("init k8s client from incluster config!")
      kubernetes.config.load_incluster_config()

    self.core_api = client.CoreV1Api()
    self.network_api = client.NetworkingV1Api()
    self.app_api = client.AppsV1Api()

  def close(self):
    self.core_api.api_client.close()
    self.network_api.api_client.close()
    self.app_api.api_client.close()

  def _raise_runtime_error(self, exception: ApiException):
    raise RuntimeError('[{}] {}'.format(exception.status,
                                        exception.reason))

  def create_or_update_ingress(self, metadata, spec, name, namespace='default'):
    ingress = client.NetworkingV1beta1Ingress(
      api_version='networking.k8s.io/v1beta1',
      kind='Ingress',
      metadata=metadata,
      spec=spec
    )
    try:
      self.network_api.read_namespaced_ingress(name, namespace)
      self.network_api.patch_namespaced_ingress(name, namespace, ingress)
      return
    except ApiException as e:
      # Http 404 indicate that the ingress is not existing.
      if e.status != HTTPStatus.NOT_FOUND:
        self._raise_runtime_error(e)
      else:
        log.debug("ingress {}/{} does not exist, try to create!".format(namespace, name))
    try:
      self.network_api.create_namespaced_ingress(namespace, ingress)
    except ApiException as e:
      self._raise_runtime_error(e)

  def delete_ingress(self, name, namespace='default'):
    try:
      self.network_api.delete_namespaced_ingress(name, namespace)
    except ApiException as e:
      self._raise_runtime_error(e)

  def get_ingress(self, name, namespace='default'):
    try:
      return self.network_api.read_namespaced_ingress(name, namespace)
    except ApiException as e:
      if e.status != HTTPStatus.NOT_FOUND:
        self._raise_runtime_error(e)

  def create_or_update_service(self,
                               metadata,
                               spec,
                               name,
                               namespace='default'):
    service = client.V1Service(
      api_version='v1',
      kind='Service',
      metadata=metadata,
      spec=spec
    )
    try:
      self.core_api.read_namespaced_service(name, namespace)
      self.core_api.patch_namespaced_service(name, namespace, service)
      return
    except ApiException as e:
      if e.status != HTTPStatus.NOT_FOUND:
        self._raise_runtime_error(e)
      else:
        log.debug("service {}/{} does not exist, try to create!".format(namespace, name))
    try:
      self.core_api.create_namespaced_service(namespace, service)
    except ApiException as e:
      self._raise_runtime_error(e)

  def delete_service(self, name, namespace='default'):
    try:
      self.core_api.delete_namespaced_service(name, namespace)
    except ApiException as e:
      if e.status != HTTPStatus.NOT_FOUND:
        self._raise_runtime_error(e)

  def get_service(self, name, namespace='default'):
    try:
      return self.core_api.read_namespaced_service(name, namespace)
    except ApiException as e:
      self._raise_runtime_error(e)

  def get_pod(self, name, namespace='default'):
    try:
      return self.core_api.read_namespaced_pod(name, namespace)
    except ApiException as e:
      # Http 404 indicate that the ingress is not existing.
      if e.status != HTTPStatus.NOT_FOUND:
        self._raise_runtime_error(e)
      else:
        log.debug("pod {}/{} does not exist!".format(namespace, name))
        return None

  def update_pod_labels(self,
                        name,
                        labels: dict,
                        namespace='default') -> bool:
    try:
      pod = self.core_api.read_namespaced_pod(name, namespace)
      pod.metadata.labels = labels
      self.core_api.patch_namespaced_pod(name, namespace, pod)
      return True
    except ApiException as e:
      if e.status != HTTPStatus.NOT_FOUND:
        self._raise_runtime_error(e)
      else:
        log.debug("pod {}/{} does not exist, update fail!".format(namespace, name))
        return False

  def get_secret(self, name, namespace='default'):
    try:
      return self.core_api.read_namespaced_secret(name, namespace)
    except ApiException as e:
      if e.status != HTTPStatus.NOT_FOUND:
        self._raise_runtime_error(e)
      else:
        log.debug("secret {}/{} does not exist".format(namespace, name))
        return None

  def get_secret_key(self, name, key, namespace='default'):
    sec = self.get_secret(name, namespace)
    return None if sec is None else sec.data.get(key)
