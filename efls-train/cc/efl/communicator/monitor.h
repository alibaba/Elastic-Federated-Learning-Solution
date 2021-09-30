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

#ifndef EFL_MONITOR_H_
#define EFL_MONITOR_H_

#include <unordered_map>
#include <functional>
#include <thread>

#include "tensorflow/core/platform/mutex.h"

namespace tensorflow {
namespace efl {

class Monitor {
 public:
  Monitor(const long long scanning_interval_milliseconds,
          const long long default_timeout_milliseconds);
  ~Monitor();

  int Register(const std::function<void()>& callback, long long timeout_milliseconds=0);
  bool Unregister(int key);

  void Start();
  void Shutdown();

 private:
  void Run();

  int cnt_ = 0;
  mutex mu_;
  std::unordered_map<int, std::pair<std::function<void()>, long long>> map_;
  volatile bool running_ = false;
  const long long scanning_interval_milliseconds_;
  const long long default_timeout_milliseconds_;
  std::thread loop_thread_;
};

} // efl
} // tensorflow

#endif // EFL_MONITOR_H_
