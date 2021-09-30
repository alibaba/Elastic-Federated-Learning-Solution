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

#ifndef EFL_SERVICE_DISCOVERY_REMOTE_KV_H_
#define EFL_SERVICE_DISCOVERY_REMOTE_KV_H_

#include <string>
#include <map>
#include <functional>

#include <tensorflow/core/lib/core/status.h>

namespace efl {

class RemoteKV {
 public:
  virtual bool Accept(const std::string& addr) = 0;
  virtual tensorflow::Status Get(const std::string& addr, std::string* val) = 0;
  virtual tensorflow::Status Put(const std::string& addr, const std::string& val) = 0;
};

class RemoteKVManager {
 public:
  static RemoteKVManager* Instance();
  // Only for testing.
  RemoteKVManager() {}
  void Register(RemoteKV* kv, int64_t priority = 0);
  tensorflow::Status Get(const std::string& addr, std::string* val);
  tensorflow::Status Put(const std::string& addr, const std::string& val);
 private:
  std::multimap<int64_t, RemoteKV*, std::greater<int64_t> > map_;
};

}  // namespace efl

#endif  // EFL_SERVICE_DISCOVERY_REMOTE_KV_H_
