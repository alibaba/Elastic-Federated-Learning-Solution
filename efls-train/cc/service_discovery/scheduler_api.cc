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

#include "cc/service_discovery/scheduler_api.h"

#include <utility>
#include <tensorflow/core/lib/core/errors.h>

#include "cc/service_discovery/remote_scheduler.h"
#include "cc/service_discovery/remote_kv.h"

namespace efl {

using namespace tensorflow;

Status StartScheduler(
    const ClusterDef& def, 
    const std::string& ip, 
    int port,
    const std::string& kvaddr, 
    std::unique_ptr<SchedulerService>* service) {
  std::unique_ptr<SchedulerService> ret(
      NewSchedulerService(def, ip, port, kvaddr));
  if (ret == nullptr) {
    return errors::Internal("Cannot create scheduler service to this target",
                            kvaddr);
  }

  TF_RETURN_IF_ERROR(ret->Start());
  *service = std::move(ret);
  return Status::OK();
}

Status GetClusterDef(const std::string& addr, ClusterDef* def) {
  string scheduler_target;
  TF_RETURN_IF_ERROR(RemoteKVManager::Instance()->Get(addr, &scheduler_target));
  std::unique_ptr<SchedulerInterface> scheduler(
      CreateRemoteScheduler(scheduler_target));
  if (scheduler == nullptr) {
    return errors::Internal("Cannot create remote scheduler for this target",
                            scheduler_target);
  }

  return scheduler->GetCluster(def);
}

Status StartReporter(
    const std::string& job, 
    int64_t task, 
    const std::string& target, 
    const std::string& kv_addr,
    int64_t interval, 
    std::unique_ptr<Reporter>* reporter) {
  std::unique_ptr<Reporter> result(
      new Reporter(
          job, task, target, kv_addr, interval,
          RemoteKVManager::Instance(), 
          CreateRemoteScheduler));
  result->Start();
  *reporter = std::move(result);
  return Status::OK();
}

}  // namespace efl

