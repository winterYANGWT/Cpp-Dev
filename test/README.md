# Tests

The `test/` directory contains the project's GoogleTest test executables.

## GoogleTest Contract

Tests use GoogleTest through CMake package config mode:

```cmake
find_package(GTest CONFIG ...)
include(GoogleTest)
```

Use `find_package(GTest CONFIG REQUIRED)` directly when the default CMake error
message is enough. Use `QUIET` followed by an immediate `message(FATAL_ERROR ...)`
when the template should provide a clearer installation diagnostic.

The template does not download GoogleTest. If CMake cannot find `GTest CONFIG`,
install GoogleTest with your package manager or build it yourself, then pass the
package location through `CMAKE_PREFIX_PATH` or `GTest_DIR`.

## Test Target Rules

- Link every GoogleTest executable to `GTest::gtest_main`.
- Register GoogleTest binaries with `gtest_discover_tests(<target>)`.
- Do not call `add_test(NAME ... COMMAND ...)` directly for GoogleTest binaries.
- Use `.cc` for test sources.
- Name cases `TEST(Suite, Case)` so CTest produces clear, unique names.
- Pass build-time-known inputs through `target_compile_definitions()` instead of
  per-test command-line arguments, so discovery works without custom argv.

When the same source is built into more than one test executable, register the
extra build with a unique suffix:

```cmake
gtest_discover_tests(example_test TEST_SUFFIX .variant)
```

For `-fno-exceptions` variants, also set:

```cmake
target_compile_definitions(example_test PRIVATE GTEST_HAS_EXCEPTIONS=0)
```

## Running Tests

Run the standard quality gate:

```sh
python3 scripts/quality.py check
```

Run only the build and CTest phase:

```sh
python3 scripts/quality.py test
```

Useful manual CMake commands:

```sh
cmake --preset quality
cmake --build --preset quality
ctest --preset quality
```

Run the tests under sanitizers with the `asan-ubsan` preset, or with the `tsan`
preset for ThreadSanitizer. The two cannot be combined:

```sh
cmake --preset tsan
cmake --build --preset tsan
ctest --preset tsan
```
