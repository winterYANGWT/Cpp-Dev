find_package(GTest CONFIG REQUIRED)
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
