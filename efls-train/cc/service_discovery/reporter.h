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

#ifndef EFL_SERVICE_DISCOVERY_REPORTER_H_
#define EFL_SERVICE_DISCOVERY_REPORTER_H_

#include <string>
#include <memory>
#include <thread>

#include <tensorflow/core/protobuf/cluster.pb.h>
#include <tensorflow/core/lib/core/status.h>
#include <tensorflow/core/platform/mutex.h>
#include <tensorflow/core/lib/core/notification.h>

#include "cc/service_discovery/remote_kv.h"
#include "cc/service_discovery/scheduler_interface.h"

namespace efl {

class Reporter {
 public:
  Reporter(
      const std::string& job, 
      int64_t task, 
      const std::string& target,
      const std::string& kv_addr, 
      int interval,
      RemoteKVManager* remote_kv_manager,
      std::function<SchedulerInterface*(const std::string&)> scheduler_creator);
  ~Reporter();
  void Start();
  void Stop();
  tensorflow::Status GetStatus();

 private:
  std::string job_;
  int64_t task_;
  std::string target_;
  std::string kv_addr_;
  int interval_;
  RemoteKVManager* remote_kv_manager_;
  std::function<SchedulerInterface*(const std::string&)> scheduler_creator_;

  std::unique_ptr<std::thread> thread_;
  std::unique_ptr<tensorflow::Notification> notification_;

  tensorflow::mutex status_mu_;
  tensorflow::Status status_;

  void Loop();
};

}  // namespace efl

#endif  // EFL_SERVICE_DISCOVERY_REPORTER_H_
