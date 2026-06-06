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

gtest_discover_tests(${PROJECT_NAME}_test)
