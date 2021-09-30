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

#include <thread>
#include <fstream>
#include <zookeeper/zookeeper.h>

#include <tensorflow/core/lib/core/errors.h>
#include <tensorflow/core/lib/random/random.h>

#include "cc/service_discovery/remote_kv.h"

namespace efl {
namespace {

using namespace tensorflow;

// for test only
class RemoteKVLocalFs : public RemoteKV {
 public:
  bool Accept(const std::string& addr) override;
  Status Get(const std::string& addr, std::string* val) override;
  Status Put(const std::string& addr, const std::string& val) override;
};

char kLocalFsPrefix[] = "/";

bool RemoteKVLocalFs::Accept(const std::string& addr) {
  if (addr.size() >= sizeof(kLocalFsPrefix) - 1) {
    return addr.substr(0, sizeof(kLocalFsPrefix) - 1) == kLocalFsPrefix;
  }

  return false;
}

Status RemoteKVLocalFs::Get(const std::string& addr, std::string* val) {
  std::ifstream is(addr.c_str());
  if (!is.is_open()) {
    return errors::InvalidArgument("open file failed:" + addr);
  }

  string tmp;
  while (std::getline(is, tmp)) {
    *val += tmp;
  }

  return Status::OK();
}

Status RemoteKVLocalFs::Put(const std::string& addr, const std::string& val) {
  std::ofstream os(addr.c_str());
  if (!os.is_open()) {
    return errors::InvalidArgument("open file failed:" + addr);
  }

  os << val;
  os.close();
  return Status::OK();
}

struct RemoteKVLocalFsRegister {
  RemoteKVLocalFsRegister() {
    RemoteKVManager::Instance()->Register(new RemoteKVLocalFs);
  }
} register_;

}  // namespace
}  // namespace efl

