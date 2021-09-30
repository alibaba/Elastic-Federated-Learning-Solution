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
#include <zookeeper/zookeeper.h>

#include <tensorflow/core/lib/core/errors.h>
#include <tensorflow/core/lib/random/random.h>

#include "cc/service_discovery/remote_kv.h"

namespace efl {
namespace {

using namespace tensorflow;

class RemoteKVZk : public RemoteKV {
 public:
  bool Accept(const std::string& addr) override;
  Status Get(const std::string& addr, std::string* val) override;
  Status Put(const std::string& addr, const std::string& val) override;

 private:
  static constexpr int kRetryCnt = 30;
  static constexpr int kSleepSec = 10;

  static Status SplitZkAddr(
      const std::string& addr, std::string* zkaddr, std::string* zknode);

  static bool ConnectToZk(const std::string& zkaddr, zhandle_t** handle);

  static bool IsHandleConnected(zhandle_t* handle);

  static bool SetNode(
      zhandle_t* handle, const std::string &path, const std::string &str);

  static bool DeleteNode(zhandle_t* handle, const std::string &path);

  static bool CreateParentPath(zhandle_t* handle, const std::string &path);

  static bool CreateNode(
      zhandle_t* handle, const std::string &path, const std::string &value);

  static bool Touch(
      zhandle_t* handle, const std::string &path, const std::string & value);

  static bool GetData(
      zhandle_t* handle, const std::string &path, std::string* str);

  static bool Close(zhandle_t* handle);
};

char kZfsPrefix[] = "zfs://";

bool RemoteKVZk::Accept(const std::string& addr) {
  if (addr.size() >= sizeof(kZfsPrefix) - 1) {
    return addr.substr(0, sizeof(kZfsPrefix) - 1) == kZfsPrefix;
  }

  return false;
}

Status RemoteKVZk::Get(const std::string& addr, std::string* val) {
  std::string zkaddr, zknode;
  TF_RETURN_IF_ERROR(SplitZkAddr(addr, &zkaddr, &zknode));
  zhandle_t* handle;
  bool succ = false;
  for (int i = 0; i < kRetryCnt; i++) {
    if (ConnectToZk(zkaddr, &handle)) {
      succ = true;
      break;
    }

    std::this_thread::sleep_for(std::chrono::seconds(kSleepSec));
  }

  if (!succ) {
    Close(handle);
    return errors::Internal("Cannot connect to zk server. ", addr);
  }

  succ = false;
  for (int i = 0; i < kRetryCnt; i++) {
    if (IsHandleConnected(handle) && GetData(handle, zknode, val)) {
      succ = true;
      break;
    }

    std::this_thread::sleep_for(std::chrono::seconds(kSleepSec));
  }

  if (!succ) {
    Close(handle);
    return errors::Unavailable("Cannot get zk node. ", addr);
  }

  Close(handle);
  return Status::OK();
}

Status RemoteKVZk::Put(const std::string& addr, const std::string& val) {
  std::string zkaddr, zknode;
  TF_RETURN_IF_ERROR(SplitZkAddr(addr, &zkaddr, &zknode));
  zhandle_t* handle;
  bool succ = false;
  for (int i = 0; i < kRetryCnt; i++) {
    if (ConnectToZk(zkaddr, &handle)) {
      succ = true;
      break;
    }

    std::this_thread::sleep_for(std::chrono::seconds(kSleepSec));
  }

  if (!succ) {
    Close(handle);
    return errors::Internal("Cannot connect to zk server. ", addr);
  }

  succ = false;
  for (int i = 0; i < kRetryCnt; i++) {
    if (IsHandleConnected(handle) && CreateParentPath(handle, zknode)) {
      if (Touch(handle, zknode, val)) {
        succ = true;
        break;
      }
    }

    std::this_thread::sleep_for(std::chrono::seconds(kSleepSec));
  }

  if (!succ) {
    Close(handle);
    return errors::Unavailable("Cannot write zk node. ", addr);
  }

  Close(handle);
  return Status::OK();
}

Status RemoteKVZk::SplitZkAddr(
    const std::string& addr, std::string* zkaddr, std::string* zknode) {
  if (addr.substr(0, sizeof(kZfsPrefix) - 1) != kZfsPrefix) {
    return errors::InvalidArgument("Not a zk addr");
  }

  std::string simple_addr = addr.substr(sizeof(kZfsPrefix) - 1);
  size_t pos = simple_addr.find('/');
  if (pos == std::string::npos) {
    *zkaddr = simple_addr;
    *zknode = "/";
  } else {
    *zkaddr = simple_addr.substr(0, pos);
    *zknode = simple_addr.substr(pos);
  }

  return Status::OK();
}

bool RemoteKVZk::ConnectToZk(const std::string& zkaddr, zhandle_t** handle) {
  *handle = zookeeper_init(
      zkaddr.c_str(), nullptr, 6000/*timeout*/, 0, nullptr, 0);
  return *handle != 0;
}

bool RemoteKVZk::IsHandleConnected(zhandle_t* handle) {
  return zoo_state(handle) == ZOO_CONNECTED_STATE;
}

bool RemoteKVZk::SetNode(
    zhandle_t* handle, const std::string &path, const std::string &str) {
  return zoo_set(handle, path.c_str(), str.c_str(), str.length(), -1) == ZOK;
}

bool RemoteKVZk::DeleteNode(zhandle_t* handle, const std::string &path) {
  return zoo_delete(handle, path.c_str(), -1) == ZOK;
}

bool RemoteKVZk::CreateParentPath(zhandle_t* handle, const std::string &path) {
  std::vector<std::string> paths = str_util::Split(path.substr(1), "/");
  paths.pop_back();
  std::string current;
  for (auto&& item : paths) {
    current += std::string("/") + item;
    int ret = zoo_create(handle, current.c_str(), "", 0,
          &ZOO_OPEN_ACL_UNSAFE, 0, NULL, 0);
    if (ret != ZOK && ret != ZNODEEXISTS) {
      return false;
    }
  }

  return true;
}

bool RemoteKVZk::CreateNode(
    zhandle_t* handle, const std::string &path, const std::string &value) {
  int ret = zoo_create(handle, path.c_str(), value.c_str(), value.length(),
                       &ZOO_OPEN_ACL_UNSAFE, 0, NULL, 0);
  if (ZOK == ret) {
    return true;
  } else if (ZNONODE == ret) {
    if (!CreateParentPath(handle, path)) {
      return false;
    }

    int ret = zoo_create(handle, path.c_str(), value.c_str(), value.length(),
                         &ZOO_OPEN_ACL_UNSAFE, 0, NULL, 0);
    return ret == ZOK;
  } else {
    return false;
  }
}

bool RemoteKVZk::Touch(
    zhandle_t* handle, const std::string &path, const std::string & value) {
  if (SetNode(handle, path, value)) {
      return true;
  }

  DeleteNode(handle, path);
  return CreateNode(handle, path, value);
}

bool RemoteKVZk::GetData(
    zhandle_t* handle, const std::string &path, std::string* str) {
  char buffer[1024];
  struct Stat stat;
  int buffer_len = sizeof(buffer);
  int ret = zoo_get(handle, path.c_str(), 0, buffer, &buffer_len, &stat);
  if (ZOK != ret) {
    return false;
  }

  if ((unsigned)stat.dataLength > sizeof(buffer)) {
    char *newBuffer = new char[stat.dataLength];
    buffer_len = stat.dataLength;
    int ret = zoo_get(
        handle, path.c_str(), 0, newBuffer, &buffer_len, &stat);
    if (ZOK != ret) {
      delete [] newBuffer;
      return false;
    }
    *str = std::string(newBuffer, (size_t)buffer_len);
    delete [] newBuffer;
  } else {
    *str = std::string(buffer, (size_t)buffer_len);
  }

  return true;
}

bool RemoteKVZk::Close(zhandle_t* handle) {
  if (handle) {
    zoo_set_context(handle, nullptr);
    zoo_set_watcher(handle, nullptr);
    return zookeeper_close(handle) == ZOK;
  }

  return true;
}

struct RemoteKVZkRegister {
  RemoteKVZkRegister() {
    RemoteKVManager::Instance()->Register(new RemoteKVZk);
  }
} register_;

}  // namespace
}  // namespace efl

