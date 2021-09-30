cmake_minimum_required(VERSION 2.8)
project(efl)

if(DEFINED ENV{PYTHON_VERSION}) 
  if($ENV{PYTHON_VERSION} STREQUAL "py3")            
    set(PYTHON "python3")
  else()
    set(PYTHON "python2")
  endif()
else()
  set(PYTHON "python2")
endif()

execute_process(COMMAND ${PYTHON} -c "from __future__ import print_function;import tensorflow as tf; print(' '.join(tf.sysconfig.get_compile_flags()),end='')" OUTPUT_VARIABLE COMPILE_FLAGS)
execute_process(COMMAND ${PYTHON} -c "from __future__ import print_function;import tensorflow as tf; print(' '.join(tf.sysconfig.get_link_flags()),end='')" OUTPUT_VARIABLE LINK_FLAGS)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DNDEBUG -Wall -fPIC -std=c++11 -O2 -D_GLIBCXX_USE_CXX11_ABI=0")

include_directories(.)
# Add external module
set(TF_PATH ${PROJECT_SOURCE_DIR}/third_party/tensorflow)
set(CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake)

include(grpc)
include_directories(${PROTOBUF_INCLUDE_DIRS} ${GRPC_INCLUDE_DIRS} ${CMAKE_CURRENT_BINARY_DIR} ${TF_PATH})
include(utils)
third_party_library_builder_autotools(zookeeper)

find_package(PythonLibs REQUIRED)
include_directories(${PYTHON_INCLUDE_DIRS})

file(GLOB_RECURSE PROTO_SOURCE "protos/*.proto")
protobuf_generate_grpc_cpp(${PROTO_SOURCE})

add_library(efl_proto STATIC protos/cluster_service.pb.cc
                             protos/cluster_service.grpc.pb.cc
                             protos/trainer_service.pb.cc
                             protos/trainer_service.grpc.pb.cc)
set_target_properties(efl_proto PROPERTIES LINK_FLAGS "${LINK_FLAGS}")
set_target_properties(efl_proto PROPERTIES COMPILE_FLAGS "${COMPILE_FLAGS}")
target_link_libraries(efl_proto libprotobuf grpc++ tensorflow_framework)

file(GLOB_RECURSE SERVICE_DISCOVERY_CC_SOURCE "cc/service_discovery/*.cc")
add_library(efl_service_discovery SHARED ${SERVICE_DISCOVERY_CC_SOURCE})
set_target_properties(efl_service_discovery PROPERTIES LINK_FLAGS "${LINK_FLAGS}")
set_target_properties(efl_service_discovery PROPERTIES COMPILE_FLAGS "${COMPILE_FLAGS}")
target_link_libraries(efl_service_discovery efl_proto libzookeeper_mt.a ${PYTHON_LIBRARIES} tensorflow_framework)

file(GLOB_RECURSE CC_SOURCE "cc/efl/*.cc")
file(GLOB_RECURSE TF_CC_SOURCE "${TF_PATH}/*.cc")
add_library(efl SHARED ${CC_SOURCE} ${TF_CC_SOURCE})
set_target_properties(efl PROPERTIES LINK_FLAGS "${LINK_FLAGS}")
set_target_properties(efl PROPERTIES COMPILE_FLAGS "${COMPILE_FLAGS}")
target_link_libraries(efl efl_service_discovery tensorflow_framework gmp)

execute_process(
  COMMAND git rev-parse HEAD
  OUTPUT_VARIABLE COMMIT)
string(STRIP "${COMMIT}" COMMIT)
execute_process(
  COMMAND cat "${CMAKE_SOURCE_DIR}/VERSION"
  OUTPUT_VARIABLE version)
string(STRIP "${version}" efl_version)
execute_process(COMMAND ${PYTHON} -c "from __future__ import print_function;import tensorflow as tf; print(tf.VERSION,end='')" OUTPUT_VARIABLE tf_version)

file(GLOB_RECURSE PYTHON_SOURCE "python/*.py")
add_custom_target(python_wheel ALL
  DEPENDS efl ${PYTHON_SOURCE} ${CMAKE_SOURCE_DIR}/python/setup.py
  COMMAND ${CMAKE_COMMAND} -E remove_directory "${CMAKE_BINARY_DIR}/python_lib"
  COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_BINARY_DIR}/python_lib"
  COMMAND ${CMAKE_COMMAND} -E copy_directory "${CMAKE_SOURCE_DIR}/python/efl" "${CMAKE_BINARY_DIR}/python_lib/efl"
  COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_SOURCE_DIR}/python/setup.py" "${CMAKE_BINARY_DIR}/python_lib/setup.py"
  COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_BINARY_DIR}/python_lib/efl/protos"
  COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_BINARY_DIR}/protos/cluster_service_pb2.py" "${CMAKE_BINARY_DIR}/python_lib/efl/protos/"
  COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_BINARY_DIR}/protos/trainer_service_pb2.py" "${CMAKE_BINARY_DIR}/python_lib/efl/protos/"
  COMMAND ${CMAKE_COMMAND} -E touch "${CMAKE_BINARY_DIR}/python_lib/efl/protos/__init__.py"
  COMMAND sed -i "s/__EFL_COMMIT__/${COMMIT}/g" ${CMAKE_BINARY_DIR}/python_lib/efl/libinfo.py
  COMMAND sed -i "s/__TF_VERSION__/${tf_version}/g" ${CMAKE_BINARY_DIR}/python_lib/efl/libinfo.py
  COMMAND sed -i "s/__EFL_VERSION__/${efl_version}/g" ${CMAKE_BINARY_DIR}/python_lib/efl/libinfo.py
  COMMAND sed -i "s/__EFL_COMMIT__/${COMMIT}/g" ${CMAKE_BINARY_DIR}/python_lib/setup.py
  COMMAND sed -i "s/__EFL_VERSION__/${efl_version}/g" ${CMAKE_BINARY_DIR}/python_lib/setup.py
  COMMAND ${CMAKE_COMMAND} -E copy "$<TARGET_FILE:efl>" "${CMAKE_BINARY_DIR}/python_lib/efl/$<TARGET_FILE_NAME:efl>"
  COMMAND ${CMAKE_COMMAND} -E copy "$<TARGET_FILE:efl_service_discovery>" "${CMAKE_BINARY_DIR}/python_lib/efl/$<TARGET_FILE_NAME:efl_service_discovery>"
  COMMAND ${PYTHON} "${CMAKE_BINARY_DIR}/python_lib/setup.py" bdist_wheel
  COMMAND ${CMAKE_COMMAND} -E remove "${CMAKE_BINARY_DIR}/efl*.whl"
  COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_BINARY_DIR}/python_lib/dist/efl*.whl" "${CMAKE_BINARY_DIR}"
)

enable_testing()
function(add_py_test test_name test_src)
  add_test(NAME ${test_name}
    COMMAND ${PYTHON} "${CMAKE_SOURCE_DIR}/test/${test_src}"
    WORKING_DIRECTORY "${CMAKE_BINARY_DIR}/python_lib")
endfunction(add_py_test)

add_py_test(empty_test empty_test.py)
add_py_test(service_discovery_test service_discovery_test.py)
add_py_test(dataio_test dataio_test.py)
add_py_test(dataset_test federal_dataset_test.py)
add_py_test(paillier_test paillier_test.py)
