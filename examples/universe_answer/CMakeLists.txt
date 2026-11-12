cmake_minimum_required(VERSION 4.2)

project(universe_answer VERSION 0.1.0 LANGUAGES CXX)

# The template does not use C++20 modules. Module scanning would add GCC-only
# flags to compile_commands.json, which clang-tidy rejects.
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)

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
# warning options instead of using the library's CMake modules.
target_compile_options(universe_answer_cli PRIVATE -Wall -Wextra -Wpedantic)
if(universe_answer_WARNINGS_AS_ERRORS)
  target_compile_options(universe_answer_cli PRIVATE -Werror)
endif()

enable_testing()

add_test(NAME universe_answer_cli COMMAND universe_answer_cli)
set_tests_properties(universe_answer_cli PROPERTIES
  PASS_REGULAR_EXPRESSION "The answer to life, the universe, and everything is 42\\."
)
