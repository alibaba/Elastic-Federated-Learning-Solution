/* Copyright (C) 2016-2021 Alibaba Group Holding Limited
  
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
==============================================================================*/

#include <Python.h>
#include <sstream>

#include <google/protobuf/text_format.h>

#include "cc/service_discovery/scheduler_api.h"

static PyObject* py_start_scheduler(PyObject* self, PyObject* args) {
  const char* cluster_def;
  Py_ssize_t cluster_len;
  const char* ip;
  Py_ssize_t ip_len;
  int port;
  const char* kv_addr;
  Py_ssize_t addr_len;
  if (!PyArg_ParseTuple(args, "s#s#is#", &cluster_def, &cluster_len, &ip, &ip_len, &port, &kv_addr, &addr_len)) {
    PyErr_SetString(
        PyExc_ValueError, "py_start_scheduler parse argument failed");    
    return nullptr;
  }

  tensorflow::ClusterDef cluster;
  if (!google::protobuf::TextFormat::ParseFromString(
          std::string(cluster_def), &cluster)) {
    PyErr_SetString(PyExc_ValueError, "Parse ClusterDef failed");
    return nullptr;
  }
  std::unique_ptr<efl::SchedulerService> ptr;
  tensorflow::Status st = efl::StartScheduler(
      cluster, std::string(ip), port, std::string(kv_addr), &ptr);
  if (st.ok()) {
    PyObject* ret =  PyLong_FromVoidPtr((void*)(ptr.release()));
    return ret;
  } else {
    PyErr_SetString(
        PyExc_ValueError, 
        (std::string("StartScheduler failed:") + st.ToString()).c_str());
    return nullptr;
  }
}

static PyObject* py_release_scheduler(PyObject* self, PyObject* args) {
  long ptr;
  if (!PyArg_ParseTuple(args, "l", &ptr)) {
    PyErr_SetString(
        PyExc_ValueError, "py_release_scheduler parse argument failed");    
    return nullptr;
  }

  efl::SchedulerService* ss = 
    reinterpret_cast<efl::SchedulerService*>(ptr);
  delete ss;
  Py_RETURN_NONE;
}

static PyObject* py_start_reporter(PyObject* self, PyObject* args) {
  const char* job;
  Py_ssize_t job_len;
  int task;
  const char* target;
  Py_ssize_t target_len;
  const char* kv_addr;
  Py_ssize_t addr_len;
  int interval;
  if (!PyArg_ParseTuple(args, "s#is#s#i", &job, &job_len, &task, 
                        &target, &target_len, &kv_addr, &addr_len, &interval)) {
    PyErr_SetString(
        PyExc_ValueError, "py_start_reporter parse argument failed");    
    return nullptr;
  }
  std::unique_ptr<efl::Reporter> ptr;
  tensorflow::Status st = efl::StartReporter(
      std::string(job), 
      task, 
      std::string(target), 
      std::string(kv_addr), 
      interval,
      &ptr);
  if (st.ok()) {
    return PyLong_FromVoidPtr((void*)(ptr.release()));
  } else {
    PyErr_SetString(
        PyExc_ValueError, 
        (std::string("StartReporter failed:") + st.ToString()).c_str());
    return nullptr;
  }
}

static PyObject* py_release_reporter(PyObject* self, PyObject* args) {
  long ptr;
  if (!PyArg_ParseTuple(args, "l", &ptr)) {
    PyErr_SetString(
        PyExc_ValueError, "py_release_scheduler parse argument failed");    
    return nullptr;
  }
  
  efl::Reporter* r = reinterpret_cast<efl::Reporter*>(ptr);
  delete r;
  Py_RETURN_NONE;
}

static PyObject* py_get_cluster_def(PyObject* self, PyObject* args) {
  const char* kv_addr;
  Py_ssize_t addr_len;
  if (!PyArg_ParseTuple(args, "s#", &kv_addr, &addr_len)) {
    PyErr_SetString(
        PyExc_ValueError, "py_get_cluster_def parse argument failed");    
    return nullptr;
  }

  tensorflow::ClusterDef def;
  tensorflow::Status st = efl::GetClusterDef(std::string(kv_addr), &def);
  if (st.ok()) {
    std::string cluster_def;
    google::protobuf::TextFormat::PrintToString(def, &cluster_def);
#if PY_MAJOR_VERSION < 3
    return PyString_FromString(cluster_def.c_str());
#else
    return PyUnicode_FromString(cluster_def.c_str());
#endif
  } else {
    if (st.code() == tensorflow::error::UNAVAILABLE) {
#if PY_MAJOR_VERSION < 3
      return PyString_FromString("unavailable");
#else
      return PyUnicode_FromString("unavailable");
#endif
    } else {
      PyErr_SetString(
        PyExc_ValueError, 
        (std::string("GetClusterDef failed:") + st.ToString()).c_str());
      return nullptr;
    }
  }
}

static PyMethodDef kMethods[] = {
  { "py_start_scheduler", &py_start_scheduler, METH_VARARGS, "start scheduler" },
  { "py_release_scheduler", &py_release_scheduler, METH_VARARGS, "release scheduler"},
  { "py_start_reporter", &py_start_reporter, METH_VARARGS, "start reporter" },
  { "py_release_reporter", &py_release_reporter, METH_VARARGS, "release release"},
  { "py_get_cluster_def", &py_get_cluster_def, METH_VARARGS, "get cluster def"},
  { NULL, NULL, 0, NULL }
};

static struct PyModuleDef libefl_service_discovery_module =
{
    PyModuleDef_HEAD_INIT,
    "libefl_service_discovery",
    "discovery\n",
    -1,
    kMethods
};

PyMODINIT_FUNC PyInit_libefl_service_discovery(void) {
  return PyModule_Create(&libefl_service_discovery_module);
}
