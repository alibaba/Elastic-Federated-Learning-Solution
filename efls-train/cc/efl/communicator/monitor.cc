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

#include "monitor.h"

namespace tensorflow {
namespace efl {

Monitor::Monitor(const long long scanning_interval_milliseconds,
                 const long long default_timeout_milliseconds)
  : scanning_interval_milliseconds_(scanning_interval_milliseconds),
    default_timeout_milliseconds_(default_timeout_milliseconds) {}

Monitor::~Monitor() {
  if (running_) {
    Shutdown();
  }
}

void Monitor::Start() {
  if (!running_) {
    running_ = true;
    loop_thread_ = std::thread(&Monitor::Run, this);
  }
}

void Monitor::Shutdown() {
  if (running_) {
    running_ = false;
    loop_thread_.join();
    mutex_lock m_lock(mu_);
    for (auto iter = map_.begin(); iter != map_.end(); iter++) {
      map_.erase(iter);
    }
  }
}

int Monitor::Register(const std::function<void()>& callback, long long timeout_milliseconds) {
  if (!running_) {
    return 0;
  }
  if (timeout_milliseconds <= 0LL) {
    timeout_milliseconds = default_timeout_milliseconds_;
  }
  auto curr_time = 
      std::chrono::duration_cast<std::chrono::milliseconds>(
          std::chrono::system_clock::now().time_since_epoch()).count();
  timeout_milliseconds += curr_time;
  mutex_lock m_lock(mu_);
  if (cnt_ == -1) {
    cnt_ = 0;
  }
  map_[++cnt_] = std::make_pair(callback, timeout_milliseconds);
  return cnt_;
}

bool Monitor::Unregister(int key) {
  mutex_lock m_lock(mu_);
  auto iter = map_.find(key);
  if (iter != map_.end()) {
    map_.erase(iter);
    return true;
  } else {
    return false;
  }
}

void Monitor::Run() {
  while(running_) {
    auto curr_time = 
      std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    {
      mutex_lock m_lock(mu_);
      for (auto iter = map_.begin(); iter != map_.end();) {
        auto timeout_milliseconds = iter->second.second;
        if (curr_time > timeout_milliseconds) {
          auto callback = iter->second.first;
          callback();
          map_.erase(iter++);
        } else {
          iter++;
        }
      }
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(scanning_interval_milliseconds_));
  }
}

} // efl
} // tensorflow
