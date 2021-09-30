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

#ifndef EFL_SERVICE_DISCOVERY_SCHEDULER_SERVICE_H_
#define EFL_SERVICE_DISCOVERY_SCHEDULER_SERVICE_H_

#include <unordered_map>
#include <unordered_set>
#include <string>
#include <vector>

#include "tensorflow/core/protobuf/cluster.pb.h"
#include "tensorflow/core/lib/core/status.h"
#include "tensorflow/core/platform/mutex.h"

namespace efl {

class SchedulerService {
 public:
  virtual ~SchedulerService() {}
  virtual tensorflow::Status Start() = 0;
  virtual void Join() = 0;
};

SchedulerService* NewSchedulerService(
    const tensorflow::ClusterDef& def, 
    const std::string& ip, 
    int port, 
    const std::string& kvaddr);

}  // namespace efl

#endif  // EFL_SERVICE_DISCOVERY_SCHEDULER_SERVICE_H_

