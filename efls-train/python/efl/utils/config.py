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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import argparse
import copy

from efl import exporter
from efl.service_discovery import service_discovery

parser = argparse.ArgumentParser(description="efl arguments")
parser.add_argument('-c', '--config', default=None)
parser.add_argument('--ckpt_dir', default=None)
parser.add_argument('--app_id', default=None)
parser.add_argument('--ps_num', default=0)
parser.add_argument('--worker_num', default=1)
parser.add_argument('--federal_role', default='leader')
parser.add_argument('--zk_addr', default=None)
parser.add_argument('--task_name', default='worker')
parser.add_argument('--task_index', default=0)
parser.add_argument('--use_default_port', action='store_false')
parser.add_argument('--peer_addr', default=None)
_CMD_ARGS, unknown = parser.parse_known_args()

service_discovery.start_service_discovery(
    _CMD_ARGS.zk_addr, int(_CMD_ARGS.ps_num),
    int(_CMD_ARGS.worker_num),
    _CMD_ARGS.task_name, int(_CMD_ARGS.task_index),
    _CMD_ARGS.use_default_port)

@exporter.export('get_app_id')
def get_app_id():
  return _CMD_ARGS.app_id

@exporter.export('get_federal_role')
def get_federal_role():
  return _CMD_ARGS.federal_role

@exporter.export('get_task_name')
def get_task_name():
  if local_mode():
    return 'worker'
  else:
    return _CMD_ARGS.task_name

@exporter.export('get_task_index')
def get_task_index():
  if local_mode():
    return 0
  else:
    return int(_CMD_ARGS.task_index)

@exporter.export('get_peer_addr')
def get_peer_addr():
  if local_mode():
    role = get_federal_role()
    if role == 'leader':
      return 'localhost:50052'
    elif role == 'follower':
      return 'localhost:50051'
    else:
      raise ValueError('Unknown federal role: {}'.format(role))
  elif _CMD_ARGS.peer_addr == None:
    raise ValueError('No input peer address.')
  else:
    return _CMD_ARGS.peer_addr

@exporter.export('get_local_addr')
def get_local_addr():
  if local_mode():
    role = get_federal_role()
    if role == 'leader':
      return 'localhost:50051'
    elif role == 'follower':
      return 'localhost:50052'
    else:
      raise ValueError('Unknown federal role: {}'.format(role))
  else:
    return service_discovery.get_local_addr(
        get_task_name(), get_task_index())

@exporter.export('get_cluster')
def get_cluster():
  if local_mode():
    raise ValueError('Local mode not support get_cluster().')
  else:
    tf_config = service_discovery.generate_tf_config_and_set_env(
      get_task_name(), get_task_index())
    tf_config = json.loads(tf_config)
    return tf_config['cluster']

@exporter.export('get_ckpt_dir')
def get_ckpt_dir():
  if _CMD_ARGS.ckpt_dir:
    return _CMD_ARGS.ckpt_dir
  return get_config("checkpoint", "output_dir")

@exporter.export('get_zk_addr')
def get_zk_addr():
  return _CMD_ARGS.zk_addr

@exporter.export('local_mode')
def local_mode():
  return get_zk_addr() is None

@exporter.export('dist_mode')
def dist_mode():
  return not local_mode()

@exporter.export('get_config_str')
def get_config_str():
  return _CMD_ARGS.config

@exporter.export('is_chief')
def is_chief():
  return get_task_name() == 'worker' and get_task_index() == 0

_CONFIG = {}
if get_config_str():
  _CONFIG = json.loads(get_config_str())

@exporter.export('get_config')
def get_config(*args, **kwargs):
  default_value = kwargs.pop("default", None)
  global _CONFIG
  value = _CONFIG
  for arg in args:
    if not isinstance(value, dict) or arg not in value:
      return default_value
    value = value[arg]
  return value

@exporter.export('get_worker_num')
def get_worker_num():
  if local_mode():
    return 1
  else:
    return int(_CMD_ARGS.worker_num)

@exporter.export('get_server_num')
def get_server_num():
  if local_mode():
    return 1
  else:
    return int(_CMD_ARGS.ps_num)
