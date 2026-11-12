find_package(GTest CONFIG QUIET)
if(NOT GTest_FOUND)
  message(FATAL_ERROR
    "GoogleTest was not found via find_package(GTest CONFIG). "
    "Install GoogleTest with your system package manager, such as apt, "
    "or build GoogleTest yourself and pass its package location to "
    "CMake with CMAKE_PREFIX_PATH or GTest_DIR."
  )
endif()
include(GoogleTest)

add_executable(${PROJECT_NAME}_test
  ${PROJECT_NAME}_test.cc
)

target_link_libraries(${PROJECT_NAME}_test
  PRIVATE
    ${PROJECT_NAME}::${PROJECT_NAME}
    GTest::gtest_main
)

project_name_configure_cxx_target(${PROJECT_NAME}_test)

gtest_discover_tests(${PROJECT_NAME}_test)
