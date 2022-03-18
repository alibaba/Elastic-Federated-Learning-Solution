#include "log.h"

#include <stdlib.h>
#include <time.h>

#include <iostream>
#include <sstream>
#include <cstring>

#include "time_utils.h"

namespace efls {

LogMessage::LogMessage(const char* fname, int line, int severity)
  : fname_(fname), line_(line), severity_(severity) {}

void LogMessage::GenerateLogMessage() {
  uint64_t now_micros = TimeUtils::NowMicros();
  time_t now_seconds = static_cast<time_t>(now_micros / 1000000);
  int32_t micros_remainder = static_cast<int32_t>(now_micros % 1000000);
  const size_t kBufferSize = 30;
  char time_buffer[kBufferSize];
  strftime(time_buffer, kBufferSize, "%Y-%m-%d %H:%M:%S",
           localtime(&now_seconds));
  fprintf(stderr, "%s.%06d: %c %s:%d [efls] %s\n", time_buffer, micros_remainder,
          "DIWEF"[severity_], fname_, line_, str().c_str());
}

namespace {

int64_t GetLogLevelFromEnv() {
  const char* log_level = getenv("EFLS_LOG_LEVEL");
  if (log_level == nullptr) {
    return INFO;
  }

  return atoi(log_level);
}

}  // namespace

LogMessage::~LogMessage() {
  static int64_t min_log_level = GetLogLevelFromEnv();
  if (likely(severity_ >= min_log_level)) {
    GenerateLogMessage();
  }
}

LogMessageFatal::LogMessageFatal(const char* file, int line)
    : LogMessage(file, line, FATAL) {}

LogMessageFatal::~LogMessageFatal() {
  GenerateLogMessage();
  abort();
}

struct timeval GetTime() {
  struct timeval t;
  gettimeofday(&t, NULL);
  return t;
}

uint64_t GetTimeInterval(const struct timeval& a,
                         const struct timeval& b) {
  return 1000000 * (b.tv_sec - a.tv_sec) + b.tv_usec - a.tv_usec;
}

}  // namespace efls
