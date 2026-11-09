cmake_minimum_required(VERSION 3.21)

project(universe_answer VERSION 0.1.0 LANGUAGES CXX)

option(universe_answer_WARNINGS_AS_ERRORS "Treat universe_answer compiler warnings as errors" OFF)

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

# The example builds against the installed package only, so it sets its own
# warning options instead of using the library's CMake modules. clang-cl takes
# MSVC-style options; the ID check covers CMake before 3.26, which leaves
# CMAKE_CXX_COMPILER_FRONTEND_VARIANT empty for MSVC.
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC"
    OR CMAKE_CXX_COMPILER_FRONTEND_VARIANT STREQUAL "MSVC")
  target_compile_options(universe_answer_cli PRIVATE /W4 /permissive-)
  if(universe_answer_WARNINGS_AS_ERRORS)
    target_compile_options(universe_answer_cli PRIVATE /WX)
  endif()
else()
  target_compile_options(universe_answer_cli PRIVATE -Wall -Wextra -Wpedantic)
  if(universe_answer_WARNINGS_AS_ERRORS)
    target_compile_options(universe_answer_cli PRIVATE -Werror)
  endif()
endif()

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
