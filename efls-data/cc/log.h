#pragma once
#include <limits>
#include <sstream>
#include <sys/time.h>
#include <stdlib.h>

namespace efls {

const int DEBUG = 0;
const int INFO = 1;
const int WARNING = 2;
const int ERROR = 3;
const int FATAL = 4;
const int NUM_SEVERITIES = 5;

class LogMessage : public std::basic_ostringstream<char> {
 public:
  LogMessage(const char* fname, int line, int severity);
  ~LogMessage();

 protected:
  void GenerateLogMessage();

 private:
  const char* fname_;
  int line_;
  int severity_;
};

class LogMessageFatal : public LogMessage {
 public:
  LogMessageFatal(const char* file, int line);
  ~LogMessageFatal();
};

#define _EFLS_LOG_INFO                                   \
  ::efls::LogMessage(__FILE__, __LINE__, ::efls::INFO)
#define _EFLS_LOG_DEBUG                                  \
  ::efls::LogMessage(__FILE__, __LINE__, ::efls::DEBUG)
#define _EFLS_LOG_WARNING                                  \
  ::efls::LogMessage(__FILE__, __LINE__, ::efls::WARNING)
#define _EFLS_LOG_ERROR                                  \
  ::efls::LogMessage(__FILE__, __LINE__, ::efls::ERROR)
#define _EFLS_LOG_FATAL                        \
  ::efls::LogMessageFatal(__FILE__, __LINE__)

#define EFLS_LOG(severity) _EFLS_LOG_##severity

#define EFLS_DLOG(severity) EFLS_LOG(severity)

#ifndef likely
#define likely(x) __builtin_expect(!!(x), 1)
#endif

#ifndef unlikely
#define unlikely(x) __builtin_expect(!!(x), 0)
#endif

#define EFLS_CHECK(condition)                          \
  if (unlikely(!(condition)))                           \
    EFLS_LOG(FATAL) << "CHECK failed: " #condition " "

#define EFLS_CHECK_NOT_NULL(condition)                          \
  if (unlikely(!(condition)))                           \
    EFLS_LOG(FATAL) << "CHECK_NOT_NULL failed: " #condition " is null ptr"

#define EFLS_CHECK_EQ(lhs, rhs)                          \
  if (unlikely(((lhs) != (rhs))))                         \
    EFLS_LOG(FATAL) << "CHECK_EQ failed: " #lhs " == " #rhs


#define EFLS_DCHECK(condition) EFLS_CHECK(condition)

struct timeval GetTime();

uint64_t GetTimeInterval(const struct timeval& a,
                         const struct timeval& b);
}  // namespace efls
