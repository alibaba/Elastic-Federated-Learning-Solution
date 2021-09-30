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

#ifndef EFL_SERVICE_DISCOVERY_SCHEDULER_API_H_
#define EFL_SERVICE_DISCOVERY_SCHEDULER_API_H_

#include <memory>
#include <string>

#include "cc/service_discovery/scheduler_service.h"
#include "cc/service_discovery/reporter.h"

namespace efl {

tensorflow::Status StartScheduler(
    const tensorflow::ClusterDef& def, 
    const std::string& ip, 
    int port,
    const std::string& kvaddr, 
    std::unique_ptr<SchedulerService>* service);

tensorflow::Status GetClusterDef(
    const std::string& addr, 
    tensorflow::ClusterDef* def);

tensorflow::Status StartReporter(
    const std::string& job, 
    int64_t task, 
    const std::string& target, 
    const std::string& kv_addr,
    int64_t interval, 
    std::unique_ptr<Reporter>* reporter);

}  // namespace efl

#endif  // EFL_SERVICE_DISCOVERY_SCHEDULER_API_H_
