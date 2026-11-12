cmake_minimum_required(VERSION 4.2)

project(mylib VERSION 0.1.0 LANGUAGES CXX)

# The template does not use C++20 modules. Module scanning would add GCC-only
# flags to compile_commands.json, which clang-tidy rejects.
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)

include(cmake/mylibOptions.cmake)
include(cmake/mylibCompiler.cmake)
include(cmake/mylibDocs.cmake)
include(cmake/mylibInstall.cmake)
include(GenerateExportHeader)

add_library(${PROJECT_NAME}
  src/${PROJECT_NAME}.cc
)
add_library(${PROJECT_NAME}::${PROJECT_NAME} ALIAS ${PROJECT_NAME})

target_compile_features(${PROJECT_NAME}
  PUBLIC
    cxx_std_20
)

mylib_configure_cxx_target(${PROJECT_NAME})

target_include_directories(${PROJECT_NAME}
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)

target_include_directories(${PROJECT_NAME}
  SYSTEM PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/include>
)

# Only patch releases are ABI compatible, so SOVERSION is always major.minor.
set_target_properties(${PROJECT_NAME} PROPERTIES
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN ON
  VERSION ${PROJECT_VERSION}
  SOVERSION ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
)

generate_export_header(${PROJECT_NAME}
  BASE_NAME ${PROJECT_NAME}
  EXPORT_FILE_NAME ${CMAKE_CURRENT_BINARY_DIR}/include/${PROJECT_NAME}/export.h
)

if(${PROJECT_NAME}_BUILD_TESTS)
  enable_testing()
  add_subdirectory(test)
endif()

if(${PROJECT_NAME}_INSTALL)
  mylib_install_package(${PROJECT_NAME})
endif()

if(${PROJECT_NAME}_BUILD_DOCS)
  mylib_add_docs_target()
endif()
