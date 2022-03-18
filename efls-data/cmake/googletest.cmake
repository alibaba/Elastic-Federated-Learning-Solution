set(GTEST_ROOT_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party/gtest)

add_subdirectory(${GTEST_ROOT_DIR} third_party/gtest)

set(GTEST_INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/third_party/googletest/googletest/include"
                       "${CMAKE_CURRENT_SOURCE_DIR}/third_party/googletest/googlemock/include")
