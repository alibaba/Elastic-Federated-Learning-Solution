# Minimum CMake required
cmake_minimum_required(VERSION 3.8)
project(efls_data CXX)

# Set C++17 as standard for the whole project
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
add_definitions(-D_GLIBCXX_USE_CXX11_ABI=0 -O0 -fno-omit-frame-pointer)

option(USE_OPENMP "Option for using open mp" ON)

# Threads: defines CMAKE_THREAD_LIBS_INIT and adds -pthread compile option
# for targets that link ${CMAKE_THREAD_LIBS_INIT}.
find_package (Threads)

if (USE_OPENMP)
  add_definitions(-DOPENMP)
  find_package(OpenMP)
  if (OPENMP_FOUND)
    message("OPENMP FOUND")
    set (CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${OpenMP_C_FLAGS}")
    set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
    set (CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${OpenMP_EXE_LINKER_FLAGS}")
  endif()
endif (USE_OPENMP)

set(CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake)
# Add external module
include(googletest)

if (USE_JEMALLOC)
  include(jemalloc)
endif(USE_JEMALLOC)

# Find IPPCrypto
find_package(IPPCrypto REQUIRED MODULE)
if (NOT IPPCRYPTO_FOUND)
  message(FATAL_ERROR "No Intel IPP Cryptography library found on the system.")
endif()
message ("IPPCP:${IPPCRYPTO_LIBRARIES}, ${IPPCRYPTO_INCLUDE_DIRS}")


#Find OpenSSL
find_package(OpenSSL REQUIRED MODULE)
message("OPENSSL lib:${OPENSSL_SSL_LIBRARY}, ${OPENSSL_INCLUDE_DIR}, ${OPENSSL_SSL_LIBRARY}, ${OPENSSL_CRYPTO_LIBRARIES}")

# Add include directories
include_directories(${GTEST_INCLUDE_DIRS}
                    ${IPP_CRYPTO_INCLUDE_DIR}
                    ${IPPCRYPTO_INCLUDE_DIRS}
                    )

file(GLOB_RECURSE CC_SOURCE "cc/*.cc")
add_library(efls_data SHARED ${CC_SOURCE})
target_link_libraries(efls_data ippcp OpenSSL::Crypto)

enable_testing()
