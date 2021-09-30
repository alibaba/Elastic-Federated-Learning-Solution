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

#include "cc/service_discovery/remote_kv.h"

#include <tensorflow/core/lib/core/errors.h>
#include <tensorflow/core/lib/random/random.h>

namespace efl {

using namespace tensorflow;

RemoteKVManager* RemoteKVManager::Instance() {
  static RemoteKVManager instance;
  return &instance;
}

void RemoteKVManager::Register(RemoteKV* kv, int64_t priority) {
  map_.emplace(priority, kv);
}

Status RemoteKVManager::Get(const std::string& addr, std::string* val) {
  for (auto&& item : map_) {
    if (item.second->Accept(addr)) {
      return item.second->Get(addr, val);
    }
  }

  return errors::Unimplemented("this kv spec is not implemented. ", addr);
}

Status RemoteKVManager::Put(const std::string& addr, const std::string& val) {
  for (auto&& item : map_) {
    if (item.second->Accept(addr)) {
      return item.second->Put(addr, val);
    }
  }

  return errors::Unimplemented("this kv spec is not implemented. ", addr);
}

}  // namespace efl

