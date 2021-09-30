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

from xfl.k8s.k8s_client import K8sClient
from xfl.common.constants import DOMAIN_NAME, INGRESS_PORT, DEFAULT_SECRET


def get_service_name(app_name, bucket_id):
  return '{}-{}'.format(app_name, bucket_id)


def get_host_name(service_name, domain_name):
  return '{}.{}'.format(service_name, domain_name)


def get_ingress_name(service_name):
  return '{}-{}'.format(service_name, 'ingress')


def create_data_join_service(
        client: K8sClient,
        app_name,
        bucket_id,
        target_port,
        namespace='default', ):
  service_name = get_service_name(app_name, bucket_id)
  client.create_or_update_service(
    metadata={
      'name': service_name,
      'namespace': 'default',
      'labels': {
        'app': app_name,
        'xfl-app': app_name,
        'bucket-id': str(bucket_id)
      },
    },
    spec={
      'ports': [
        {
          'port': INGRESS_PORT,
          'targetPort': target_port,
          'protocol': 'TCP'
        }
      ],
      'selector': {
        'xfl-app': app_name,
        'bucket-id': str(bucket_id)
      },
      'type': 'ClusterIP'
    },
    namespace=namespace,
    name=service_name
  )


def release_data_join_service(client: K8sClient, app_name, bucket_id, namespace='default'):
  service_name = get_service_name(app_name, bucket_id)
  client.delete_service(service_name, namespace)


def create_data_join_ingress(
        client: K8sClient,
        app_name,
        bucket_id,
        namespace='default'):
  service_name = get_service_name(app_name, bucket_id)
  host_name = get_host_name(service_name, DOMAIN_NAME)
  ing_name = get_ingress_name(service_name)
  client.create_or_update_ingress(
    metadata={
      'name': ing_name,
      'namespace': namespace,
      'annotations': {
        'kubernetes.io/ingress.class': 'nginx',
        'nginx.ingress.kubernetes.io/ssl-redirect': 'true',
        'nginx.ingress.kubernetes.io/backend-protocol': 'GRPC',
      },
      'labels': {
        'app': app_name,
        'xfl-app': app_name,
        'bucket-id': str(bucket_id)
      },
    },
    spec={
      'rules': [
        {
          'host': host_name,
          'http':
            {
              'paths': [
                {
                  'path': '/',
                  'pathType': 'Prefix',
                  'backend': {
                    'serviceName': service_name,
                    'servicePort': INGRESS_PORT
                  }
                }

              ]
            }
        }
      ],
      'tls': [
        {
          'secretName': DEFAULT_SECRET,
          'hosts': [host_name]
        }
      ]
    },
    namespace=namespace,
    name=ing_name
  )


def release_data_join_ingress(client: K8sClient, app_name, bucket_id, namespace='default'):
  service_name = get_service_name(app_name, bucket_id)
  ingress_name = get_ingress_name(service_name)
  client.delete_ingress(ingress_name, namespace)
