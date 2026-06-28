cmake_minimum_required(VERSION 3.21)

project(universe_answer VERSION 0.1.0 LANGUAGES CXX)

find_package(project_name CONFIG REQUIRED)

add_executable(universe_answer_cli
  src/main.cc
)

target_link_libraries(universe_answer_cli
  PRIVATE
    project_name::project_name
)

set_target_properties(universe_answer_cli PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)

if(WIN32)
  add_custom_command(TARGET universe_answer_cli POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy -t $<TARGET_FILE_DIR:universe_answer_cli> $<TARGET_RUNTIME_DLLS:universe_answer_cli>
    COMMAND_EXPAND_LISTS
  )
endif()

enable_testing()

add_test(NAME universe_answer_cli COMMAND universe_answer_cli)
set_tests_properties(universe_answer_cli PROPERTIES
  PASS_REGULAR_EXPRESSION "The answer to life, the universe, and everything is 42\\."
)
