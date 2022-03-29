include (ExternalProject)
ExternalProject_Add(ipp
  PREFIX ipp
  SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party/ipp-crypto
  BUILD_IN_SOURCE 1
  CONFIGURE_COMMAND ${CMAKE_COMMAND} -DARCH=intel64 -DCMAKE_INSTALL_PREFIX=/opt/intel/ippcp
  BUILD_COMMAND ${MAKE}
  )

ExternalProject_Get_Property(ipp SOURCE_DIR)
message("Source dir of ipp: ${SOURCE_DIR}")

set(IPP_SOURCED_DIR ${SOURCE_DIR})

