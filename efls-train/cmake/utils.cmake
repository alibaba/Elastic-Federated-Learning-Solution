set(_PROTOBUF_PROTOC $<TARGET_FILE:protoc>)

function(protobuf_generate_cpp)
  if(NOT ARGN)
    message(SEND_ERROR "Error: PROTOBUF_GENERATE_CPP() called without any proto files")
    return()
  endif()

  set(_protobuf_include_path -I ${PROTOBUF_INCLUDE_DIRS} -I ${CMAKE_SOURCE_DIR})
  foreach(FIL ${ARGN})
    get_filename_component(ABS_FIL ${FIL} ABSOLUTE)
    get_filename_component(FIL_WE ${FIL} NAME_WE)
    file(RELATIVE_PATH REL_FIL ${CMAKE_CURRENT_SOURCE_DIR} ${ABS_FIL})
    get_filename_component(REL_DIR ${REL_FIL} DIRECTORY)
    set(RELFIL_WE "${CMAKE_CURRENT_BINARY_DIR}/${REL_DIR}/${FIL_WE}")
    add_custom_command(
      OUTPUT "${RELFIL_WE}.pb.cc"
             "${RELFIL_WE}.pb.h"
      COMMAND ${_PROTOBUF_PROTOC}
      ARGS --cpp_out=${CMAKE_BINARY_DIR} ${_protobuf_include_path} ${CMAKE_CURRENT_SOURCE_DIR}/${REL_FIL}
      DEPENDS ${ABS_FIL} ${_PROTOBUF_PROTOC} grpc_cpp_plugin
      WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
      COMMENT "Running C++ protocol buffer compiler on ${FIL}"
      VERBATIM)

    set_source_files_properties("${RELFIL_WE}.pb.cc" "${RELFIL_WE}.pb.h" PROPERTIES GENERATED TRUE)
  endforeach()
endfunction()

function(protobuf_generate_grpc_cpp)
  if(NOT ARGN)
    message(SEND_ERROR "Error: PROTOBUF_GENERATE_GRPC_CPP() called without any proto files")
    return()
  endif()

  set(_protobuf_include_path -I . -I ${PROTOBUF_INCLUDE_DIRS} -I ${TF_PATH})
  foreach(FIL ${ARGN})
    get_filename_component(ABS_FIL ${FIL} ABSOLUTE)
    get_filename_component(FIL_WE ${FIL} NAME_WE)
    file(RELATIVE_PATH REL_FIL ${CMAKE_CURRENT_SOURCE_DIR} ${ABS_FIL})
    get_filename_component(REL_DIR ${REL_FIL} DIRECTORY)
    set(RELFIL_WE "${CMAKE_CURRENT_BINARY_DIR}/${REL_DIR}/${FIL_WE}")
    add_custom_command(
      OUTPUT "${RELFIL_WE}.grpc.pb.cc"
             "${RELFIL_WE}.grpc.pb.h"
             "${RELFIL_WE}_mock.grpc.pb.h"
             "${RELFIL_WE}.pb.cc"
             "${RELFIL_WE}.pb.h"
             "${RELFIL_WE}_pb2.py"
      COMMAND ${_PROTOBUF_PROTOC}
      ARGS --grpc_out=generate_mock_code=true:${CMAKE_CURRENT_BINARY_DIR}
           --cpp_out=${CMAKE_CURRENT_BINARY_DIR}
           --python_out=${CMAKE_CURRENT_BINARY_DIR}
           --plugin=protoc-gen-grpc=$<TARGET_FILE:grpc_cpp_plugin>
           ${_protobuf_include_path}
           ${REL_FIL}
      DEPENDS ${ABS_FIL} ${_PROTOBUF_PROTOC} grpc_cpp_plugin
      WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
      COMMENT "Running gRPC C++ protocol buffer compiler on ${FIL}"
      VERBATIM)

      set_source_files_properties("${RELFIL_WE}.grpc.pb.cc" "${RELFIL_WE}.grpc.pb.h" "${RELFIL_WE}_mock.grpc.pb.h" "${RELFIL_WE}.pb.cc" "${RELFIL_WE}.pb.h" "${RELFIL_WE}_pb2.py" PROPERTIES GENERATED TRUE)
  endforeach()
endfunction()

# build third_party libraries using autotools
function (third_party_library_builder_autotools arg)
    list(LENGTH ARGV argv_len)
    set(i 0)
    while (i LESS ${argv_len})
        list(GET ARGV ${i} argv_value)
	message(STATUS "Start to build third_party library: ${argv_value}")
	execute_process(COMMAND bash -c "
	    cd ${PROJECT_SOURCE_DIR}/third_party/${argv_value};
            mkdir -p build;
            ./configure --prefix=$(pwd)/build CXXFLAGS='-D_GLIBCXX_USE_CXX11_ABI=0' LDFLAGS='-D_GLIBCXX_USE_CXX11_ABI=0';
            make;
            make install;
            cd ${PROJECT_SOURCE_DIR}")
	if (EXISTS "${PROJECT_SOURCE_DIR}/third_party/${argv_value}/build/include")
    include_directories("${PROJECT_SOURCE_DIR}/third_party/${argv_value}/build/include")
	endif ()
	if (EXISTS "${PROJECT_SOURCE_DIR}/third_party/${argv_value}/build/lib")
            link_directories("${PROJECT_SOURCE_DIR}/third_party/${argv_value}/build/lib")
	endif ()
	if (EXISTS "${PROJECT_SOURCE_DIR}/third_party/${argv_value}/build/lib64")
            link_directories("${PROJECT_SOURCE_DIR}/third_party/${argv_value}/build/lib64")
	endif ()
	math(EXPR i "${i} + 1")
    endwhile ()
endfunction ()
