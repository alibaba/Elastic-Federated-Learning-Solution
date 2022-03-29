#pragma once

#include <sys/time.h>
#include <time.h>
#include <cstdint>

namespace efls {

class TimeUtils {
 public:
  static uint64_t NowMicros() {
    struct timeval  tv;
    gettimeofday(&tv, NULL);
    return static_cast<uint64_t>(tv.tv_sec) * 1000000 + tv.tv_usec;
  }
};

}  // namespace efls
