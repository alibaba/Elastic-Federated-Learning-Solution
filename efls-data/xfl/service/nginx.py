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

NGINX_TEMPLATE = \
'''
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    map $http_servicename $custom_port {
        %s
    }
    server {
        listen       80 http2;
        server_name  localhost;

        location / {
            grpc_pass grpc://127.0.0.1:$custom_port;
        }
    }
}
'''
if 'NGINX_CMD' in os.environ:
  NGINX_CMD = os.environ['NGINX_CMD']
else:
  NGINX_CMD =  'nginx'

class Nginx(object):
  def __init__(self, job_name: str, bucket_num: int, base_port: int =50051):
    self._job_name = job_name
    self._bucket_num = bucket_num
    self._base_port = base_port

    self._map_str = ''
    for i in range(bucket_num):
      self._map_str += "{}-{} {};\n".format(job_name, i, base_port+i)
      self._map_str += ' '*8
    self._content = NGINX_TEMPLATE%(self._map_str)

  def dumps(self, path: str):
    with open(path, 'w') as f:
      f.write(self._content)

  def get_content(self):
    return self._content

  def stop(self):
    cmd = '{0} -s stop'.format(NGINX_CMD)
    os.system(cmd)

  def start(self, conf_path:str):
    cmd = '{0} -c {1}'.format(NGINX_CMD, conf_path)
    os.system(cmd)
