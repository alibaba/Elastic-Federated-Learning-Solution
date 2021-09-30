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

#include "cc/service_discovery/scheduler.h"

#include <chrono>
#include <thread>

#include <tensorflow/core/lib/core/errors.h>
#include <tensorflow/core/lib/random/random.h>
#include <tensorflow/core/util/env_var.h>

namespace efl {

using namespace tensorflow;

const std::string kRequired = "required";
const std::string kScheduler = "scheduler";

Scheduler::Scheduler(const ClusterDef& def) {
  for (auto&& job : def.job()) {
    JobDef* ndef = nullptr;
    for (auto&& task : job.tasks()) {
      if (task.second == kRequired || task.second == kScheduler) {
        workers_.insert(ToSpec(job.name(), task.first));

        if (ndef == nullptr) {
          ndef = cluster_.add_job();
          ndef->set_name(job.name());
        }

        ndef->mutable_tasks()->insert(task);
      }
    }
  }

  version_ = random::New64() & 0xFFFFFFFF00000000L;
}

Scheduler::~Scheduler() {
}

Status Scheduler::RegisterNode(const std::string& job, 
                               int64_t id,
                               const std::string& addr, 
                               int64_t my_version,
                               int64_t* version) {
  mutex_lock lock(mu_);
  std::string spec = ToSpec(job, id);
  if (workers_.find(spec) == workers_.end()) {
    return errors::InvalidArgument(
        "Server Spec is not in Scheduler's ClusterSpec: " + spec);
  }

  auto iter = target_.find(spec);
  if (iter != target_.end() && iter->second != addr && version_ == my_version) {
    LOG(INFO) << "Scheduler has detected server fail: " << spec
               << " Failed On: " << iter->second << " Restart On: " << addr;
    if (target_.size() == workers_.size()) {
      version_++;
      LOG(INFO) << "Change Version To: " << version_;
    }

    target_.clear();
    target_[spec] = addr;
  } else if (iter == target_.end() && version_ == my_version) {
    LOG(INFO) << "Server Registered : " << spec << " on " << addr;
    target_[spec] = addr;
  } else if (version_ != my_version) {
    LOG(INFO) << "Server Version Mismatch, Clear it : "
              << spec << " on " << addr;
  }

  *version = version_;
  return Status::OK();
}

Status Scheduler::GetCluster(tensorflow::ClusterDef* result) {
  mutex_lock lock(mu_);
  if (workers_.size() != target_.size()) {
    std::vector<std::string> server_not_ready;
    for (auto&& item : workers_) {
      if (target_.find(item) == target_.end()) {
        server_not_ready.push_back(item);
      }
    }

    std::string log = "Some Server is not ready (" +
      std::to_string(server_not_ready.size()) + "). [";
    if (server_not_ready.size() > 3) {
      for (int i = 0; i < 3; i++) {
        log = log + server_not_ready[i] + ", ";
      }

      log = log + "etc...]";
    } else {
      for (size_t i = 0; i < server_not_ready.size() - 1; i++) {
        log = log + server_not_ready[i] + ", ";
      }

      log = log + server_not_ready.back() + "]";
    }

    return errors::Unavailable(log);
  } else {
    auto fn = [&, this](tensorflow::ClusterDef* def) {
      def->clear_job();
      for (auto&& job : cluster_.job()) {
        JobDef* ndef = def->add_job();
        ndef->set_name(job.name());
        for (auto&& task : job.tasks()) {
          auto spec = ToSpec(job.name(), task.first);
          auto it = target_.find(spec);
          if (it != target_.end()) {
            (*ndef->mutable_tasks())[task.first] = it->second;
          }
        }
      }
    };

    fn(result);
    return Status::OK();
  }
}

}  // namespace efl
