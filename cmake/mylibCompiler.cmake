# The template supports only GCC and Clang on Linux. Both take GNU-style
# options; the template has no MSVC-style options, so MSVC and clang-cl fail
# here instead of getting options that they do not understand. AppleClang
# takes the same options as Clang, so it is not rejected.
function(mylib_check_compiler)
  if(CMAKE_CXX_COMPILER_FRONTEND_VARIANT STREQUAL "MSVC"
      OR NOT CMAKE_CXX_COMPILER_ID MATCHES "^(GNU|Clang|AppleClang)$")
    message(FATAL_ERROR "${PROJECT_NAME} supports only GCC and Clang with GNU-style options, not ${CMAKE_CXX_COMPILER_ID} (${CMAKE_CXX_COMPILER})")
  endif()
endfunction()

function(mylib_configure_cxx_target target)
  mylib_check_compiler()

  set_target_properties(${target} PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
  )

  target_compile_options(${target}
    PRIVATE
      -Wall
      -Wextra
      -Wpedantic
  )

  if(${PROJECT_NAME}_WARNINGS_AS_ERRORS)
    target_compile_options(${target}
      PRIVATE
        -Werror
    )
  endif()

  if(${PROJECT_NAME}_ENABLE_SANITIZERS)
    target_compile_options(${target}
      PRIVATE
        -fsanitize=address,undefined
        -fno-sanitize-recover=all
        -fno-omit-frame-pointer
    )
    target_link_options(${target}
      PRIVATE
        -fsanitize=address,undefined
    )
  endif()

  if(${PROJECT_NAME}_ENABLE_THREAD_SANITIZER)
    target_compile_options(${target}
      PRIVATE
        -fsanitize=thread
        -fno-omit-frame-pointer
    )
    target_link_options(${target}
      PRIVATE
        -fsanitize=thread
    )
  endif()

  # Coverage instrumentation uses the same GNU-style compilers as the sanitizers.
  if(${PROJECT_NAME}_ENABLE_COVERAGE)
    target_compile_options(${target}
      PRIVATE
        --coverage
        -O0
    )
    target_link_options(${target}
      PRIVATE
        --coverage
    )
  endif()
endfunction()

function(mylib_configure_cxx_interface_target target)
  mylib_check_compiler()

  target_compile_features(${target}
    INTERFACE
      cxx_std_20
  )

  target_compile_options(${target}
    INTERFACE
      $<BUILD_INTERFACE:-std=c++20>
      $<BUILD_INTERFACE:-Wall>
      $<BUILD_INTERFACE:-Wextra>
      $<BUILD_INTERFACE:-Wpedantic>
  )

  if(${PROJECT_NAME}_WARNINGS_AS_ERRORS)
    target_compile_options(${target}
      INTERFACE
        $<BUILD_INTERFACE:-Werror>
    )
  endif()

  if(${PROJECT_NAME}_ENABLE_SANITIZERS)
    target_compile_options(${target}
      INTERFACE
        $<BUILD_INTERFACE:-fsanitize=address,undefined>
        $<BUILD_INTERFACE:-fno-sanitize-recover=all>
        $<BUILD_INTERFACE:-fno-omit-frame-pointer>
    )
    target_link_options(${target}
      INTERFACE
        $<BUILD_INTERFACE:-fsanitize=address,undefined>
    )
  endif()

  if(${PROJECT_NAME}_ENABLE_THREAD_SANITIZER)
    target_compile_options(${target}
      INTERFACE
        $<BUILD_INTERFACE:-fsanitize=thread>
        $<BUILD_INTERFACE:-fno-omit-frame-pointer>
    )
    target_link_options(${target}
      INTERFACE
        $<BUILD_INTERFACE:-fsanitize=thread>
    )
  endif()

  # Coverage instrumentation uses the same GNU-style compilers as the sanitizers.
  if(${PROJECT_NAME}_ENABLE_COVERAGE)
    target_compile_options(${target}
      INTERFACE
        $<BUILD_INTERFACE:--coverage>
        $<BUILD_INTERFACE:-O0>
    )
    target_link_options(${target}
      INTERFACE
        $<BUILD_INTERFACE:--coverage>
    )
  endif()
endfunction()
