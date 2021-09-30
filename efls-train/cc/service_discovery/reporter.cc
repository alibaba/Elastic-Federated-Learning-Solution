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

#include "cc/service_discovery/reporter.h"

#include <utility>
#include <tensorflow/core/lib/core/errors.h>

namespace efl {

using namespace tensorflow;

Reporter::Reporter(
    const std::string& job, 
    int64_t task, 
    const std::string& target,
    const std::string& kv_addr, 
    int inteval,
    RemoteKVManager* remote_kv_manager,
    std::function<SchedulerInterface*(const std::string&)> scheduler_creator)
  : job_(job), task_(task), 
    target_(target), kv_addr_(kv_addr),
    interval_(inteval),
    remote_kv_manager_(remote_kv_manager),
    scheduler_creator_(scheduler_creator) { }

Reporter::~Reporter() {
  Stop();
}

void Reporter::Start() {
  notification_.reset(new Notification);
  thread_.reset(new std::thread(&Reporter::Loop, this));
}

void Reporter::Stop() {
  if (thread_ != nullptr) {
    notification_->Notify();
    thread_->join();
    notification_.reset(nullptr);
    thread_.reset(nullptr);
  }
}

void Reporter::Loop() {
  int64_t version = -1;
  std::unique_ptr<SchedulerInterface> scheduler;
  while (true) {
    auto fn = [&] () -> Status {
      if (scheduler == nullptr) {
        string scheduler_addr;
        TF_RETURN_IF_ERROR(
            remote_kv_manager_->Get(kv_addr_, &scheduler_addr));
        scheduler.reset(scheduler_creator_(scheduler_addr));
        if (scheduler == nullptr) {
          return errors::Internal("Scheduler Creator Error");
        }
      }

      int64_t new_version;
      TF_RETURN_IF_ERROR(
          scheduler->RegisterNode(
              job_, task_, target_, version, &new_version));
      if (new_version != version) {
        LOG(INFO) << "Update version from  " << version <<
            " to " << new_version;
        version = new_version;
      }
      return Status::OK();
    };

    Status st = fn();
    {
      mutex_lock lock(status_mu_);
      status_ = st;
    }

    if (!st.ok()) {
      LOG(ERROR) << "Register Server Failed due to " << st.ToString();
      scheduler.reset(nullptr);
    }

    if (WaitForNotificationWithTimeout(
        notification_.get(), interval_ * 1000000)) {
      break;
    }
  }
}

Status Reporter::GetStatus() {
  mutex_lock lock(status_mu_);
  return status_;
}

}  // namespace efl

