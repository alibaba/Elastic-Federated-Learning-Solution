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

#ifndef EFL_SERVICE_DISCOVERY_SCHEDULER_INTERFACE_H_
#define EFL_SERVICE_DISCOVERY_SCHEDULER_INTERFACE_H_

#include <unordered_map>
#include <unordered_set>
#include <string>
#include <vector>

#include "tensorflow/core/protobuf/cluster.pb.h"
#include "tensorflow/core/lib/core/status.h"
#include "tensorflow/core/platform/mutex.h"

#include "protos/cluster_service.grpc.pb.h"

namespace efl {

class SchedulerInterface {
 public:
  virtual ~SchedulerInterface() {}
  virtual tensorflow::Status RegisterNode(
      const std::string& job, 
      int64_t id,
      const std::string& addr, 
      int64_t my_version,
      int64_t* version) = 0;
  virtual tensorflow::Status GetCluster(
      tensorflow::ClusterDef* result) = 0;
};

}  // namespace efl

#endif  // EFL_SERVICE_DISCOVERY_SCHEDULER_INTERFACE_H_
