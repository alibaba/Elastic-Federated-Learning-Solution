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

import os
import sys 
import time
import json
import socket
import subprocess
import multiprocessing

import google.protobuf.text_format as text_format
from tensorflow.core.protobuf import cluster_pb2
from tensorflow.python.training import server_lib

from efl import exporter
from efl.libefl_service_discovery import *

def _to_bytes(data):
  if sys.version_info < (3, 0):
    return bytes(data)
  else:
    return bytes(data, 'utf8')

def _start_scheduler(cluster, ip, port, kv_addr):
  return py_start_scheduler(
    _to_bytes(str(cluster)),
    _to_bytes(str(ip)),
    port,
    _to_bytes(str(kv_addr)))

def _release_scheduler(ptr):
  py_release_scheduler(ptr)

def _start_reporter(task_name, task_index, target, kv_addr, interval):
   return py_start_reporter(
     _to_bytes(str(task_name)),
     task_index,
     _to_bytes(str(target)),
     _to_bytes(str(kv_addr)),
     interval)

def _release_reporter(ptr):
  py_release_reporter(ptr)

def _get_cluster(kv_addr):
  cluster_def = py_get_cluster_def(_to_bytes(kv_addr))
  if cluster_def == "unavailable":
    return None
  else:
    ret = text_format.Parse(
      cluster_def, cluster_pb2.ClusterDef())
    return ret

@exporter.export("ServiceDiscovery")
class ServiceDiscovery(object):
  def __init__(self, kv_addr, ps_num, worker_num,
               job, task, use_default_port):
    self._job = job
    self._task = task
    self._kv_addr = kv_addr
    self._ps_num = ps_num
    self._worker_num = worker_num
    self._ip = self._get_ip()
    self._port = self._get_port(use_default_port=use_default_port)
    self._ip_addr = '{}:{}'.format(self._ip, self._port)
    self._scheduler = None
    self._reporter = None
    self._maybe_create_scheduler()
    self._create_reporter()

  def _get_ip(self):
    return socket.gethostbyname(socket.gethostname())    

  def _get_port(self, use_default_port=True):
    if use_default_port:
      return 50151
    else:
      port = None
      sockets = None
      try:
        s = socket.socket()
        s.bind(('',0))
        port = s.getsockname()[1]
        sockets = s
      finally:
        if sockets is not None:
          sockets.close()
      if port is not None:
        return port
      else:
        raise ValueError('get port failed')

  def _maybe_create_scheduler(self):
    if self._job == "scheduler":
      cluster = {
        "scheduler": ["scheduler"],
        "ps": ["required"] * self._ps_num,
        "worker": ["required"] * self._worker_num
      }

      cluster = server_lib.ClusterSpec(cluster)
      self._scheduler = _start_scheduler(
        cluster.as_cluster_def(),
        self._ip,
        0,
        self._kv_addr)  
      if self._scheduler is None:
        raise ValueError("start scheduler failed")  

  def _create_reporter(self):
    self._reporter = _start_reporter(
      self._job,
      self._task,
      self._ip_addr,
      self._kv_addr,
      10)  
    if self._reporter is None:
      raise ValueError("start reporter failed")  
  
  def get_cluster(self):
    wait_time = 10
    try_times = 60
    while try_times != 0:
      try_times -= 1
      ret = _get_cluster(self._kv_addr)
      if ret is None:
        time.sleep(wait_time)
        if try_times == 0:
          raise ValueError("get cluster failed")
      else:
        return ret

  def __del__(self):
    if self._scheduler is not None:
      _release_scheduler(self._scheduler)
    if self._reporter is not None:
      _release_reporter(self._reporter)

_TF_CLUSTER = None
@exporter.export("start_service_discovery")
def start_service_discovery(  
  kv_addr, 
  ps_num, 
  worker_num, 
  job, 
  task,
  use_default_port,
  is_test=False):
  if ps_num == 0 and worker_num == 1:
    return None
  global _TF_CLUSTER
  if _TF_CLUSTER is not None:
    return _TF_CLUSTER
  q = multiprocessing.Queue()
  p = multiprocessing.Process(
    target=_get_cluster_process, 
    args=(kv_addr, ps_num, worker_num, job, task,
          q, use_default_port, is_test))
  p.start()
  p.join()
  ret = q.get()
  cluster_def = cluster_pb2.ClusterDef()
  cluster_def.ParseFromString(ret)  
  _TF_CLUSTER = cluster_def
  return cluster_def

def _get_cluster_process(kv_addr, ps_num, worker_num,
                         job, task, q, use_default_port, is_test):
  sd = ServiceDiscovery(kv_addr, ps_num, worker_num, job, task,
                        use_default_port)
  cluster = sd.get_cluster()
  q.put(cluster.SerializeToString())
  if is_test:
    time.sleep(15)

@exporter.export("generate_tf_config_and_set_env")
def generate_tf_config_and_set_env(job, task):
  global _TF_CLUSTER
  if _TF_CLUSTER is None:
    raise ValueError("call efl.start_service_discovery first")
  cluster_def = _TF_CLUSTER
  task_index = task
  task = {"type": job, "index": task_index}
  cluster = {}
  for item in cluster_def.job:
    for k, v in sorted(item.tasks.items()):
      name = item.name
      items = v.split(":")
      if len(items) < 2:
        raise ValueError("invalid addr:", v)
      addr = ":".join(items[:2])
      if name in cluster:
        cluster[name] = cluster[name] + [addr]
      else:
        cluster[name] = [addr]
  tf_config = json.dumps({"task": task, "cluster": cluster})
  os.environ['TF_CONFIG'] = tf_config
  return tf_config

def get_local_addr(task_name, task_index):
  return _get_addr_impl(
    task_name, task_index)

def _get_addr_impl(task_name, task_index):
  global _TF_CLUSTER
  if _TF_CLUSTER is None:
    raise ValueError("call efl.start_service_discovery first")
  cluster = _TF_CLUSTER
  addr = None
  for job in cluster.job:
    if job.name == task_name:
      if task_index not in job.tasks:
        raise ValueError("can't found addr")
      addr = job.tasks[task_index]
      break
  if addr is None:
    raise ValueError("can't found addr")    
  items = addr.split(":")
  return "{}:50051".format(items[0])
