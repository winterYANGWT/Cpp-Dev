find_package(GTest CONFIG QUIET)
if(NOT GTest_FOUND)
  message(FATAL_ERROR
    "GoogleTest was not found via find_package(GTest CONFIG). "
    "Install GoogleTest with your system package manager, such as apt, Homebrew, "
    "or vcpkg, or build GoogleTest yourself and pass its package location to "
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

if(WIN32)
  # Make shared-library DLLs available before GTest post-build discovery runs.
  add_custom_command(TARGET ${PROJECT_NAME}_test POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy -t $<TARGET_FILE_DIR:${PROJECT_NAME}_test> $<TARGET_RUNTIME_DLLS:${PROJECT_NAME}_test>
    COMMAND_EXPAND_LISTS
  )
endif()

gtest_discover_tests(${PROJECT_NAME}_test)
