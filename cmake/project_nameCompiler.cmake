# clang-cl has the Clang compiler ID but takes MSVC-style options, so options
# are chosen by the compiler frontend rather than by the compiler ID. The ID
# check is still needed because CMake before 3.26 leaves
# CMAKE_CXX_COMPILER_FRONTEND_VARIANT empty for MSVC.
function(project_name_uses_msvc_options out_var)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC"
      OR CMAKE_CXX_COMPILER_FRONTEND_VARIANT STREQUAL "MSVC")
    set(${out_var} TRUE PARENT_SCOPE)
  else()
    set(${out_var} FALSE PARENT_SCOPE)
  endif()
endfunction()

# Sanitizers are supported with GCC and with Clang's GNU-style frontend, but
# not with MSVC or clang-cl.
function(project_name_supports_sanitizers out_var)
  project_name_uses_msvc_options(msvc_options)
  if(NOT msvc_options AND CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    set(${out_var} TRUE PARENT_SCOPE)
  else()
    set(${out_var} FALSE PARENT_SCOPE)
  endif()
endfunction()

function(project_name_configure_cxx_target target)
  set_target_properties(${target} PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
  )

  project_name_uses_msvc_options(msvc_options)
  project_name_supports_sanitizers(sanitizers_supported)

  if(msvc_options)
    target_compile_options(${target}
      PRIVATE
        /W4
        /permissive-
    )
  else()
    target_compile_options(${target}
      PRIVATE
        -Wall
        -Wextra
        -Wpedantic
    )
  endif()

  if(${PROJECT_NAME}_WARNINGS_AS_ERRORS)
    if(msvc_options)
      target_compile_options(${target}
        PRIVATE
          /WX
      )
    else()
      target_compile_options(${target}
        PRIVATE
          -Werror
      )
    endif()
  endif()

  if(${PROJECT_NAME}_ENABLE_SANITIZERS)
    if(sanitizers_supported)
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
    else()
      message(WARNING "${PROJECT_NAME}_ENABLE_SANITIZERS is only supported with GCC and Clang, not with MSVC or clang-cl")
    endif()
  endif()

  if(${PROJECT_NAME}_ENABLE_THREAD_SANITIZER)
    if(sanitizers_supported)
      target_compile_options(${target}
        PRIVATE
          -fsanitize=thread
          -fno-omit-frame-pointer
      )
      target_link_options(${target}
        PRIVATE
          -fsanitize=thread
      )
    else()
      message(WARNING "${PROJECT_NAME}_ENABLE_THREAD_SANITIZER is only supported with GCC and Clang, not with MSVC or clang-cl")
    endif()
  endif()
endfunction()

function(project_name_configure_cxx_interface_target target)
  target_compile_features(${target}
    INTERFACE
      cxx_std_20
  )

  project_name_uses_msvc_options(msvc_options)
  project_name_supports_sanitizers(sanitizers_supported)

  if(msvc_options)
    target_compile_options(${target}
      INTERFACE
        $<BUILD_INTERFACE:/std:c++20>
        $<BUILD_INTERFACE:/W4>
        $<BUILD_INTERFACE:/permissive->
    )
  else()
    target_compile_options(${target}
      INTERFACE
        $<BUILD_INTERFACE:-std=c++20>
        $<BUILD_INTERFACE:-Wall>
        $<BUILD_INTERFACE:-Wextra>
        $<BUILD_INTERFACE:-Wpedantic>
    )
  endif()

  if(${PROJECT_NAME}_WARNINGS_AS_ERRORS)
    if(msvc_options)
      target_compile_options(${target}
        INTERFACE
          $<BUILD_INTERFACE:/WX>
      )
    else()
      target_compile_options(${target}
        INTERFACE
          $<BUILD_INTERFACE:-Werror>
      )
    endif()
  endif()

  if(${PROJECT_NAME}_ENABLE_SANITIZERS)
    if(sanitizers_supported)
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
    else()
      message(WARNING "${PROJECT_NAME}_ENABLE_SANITIZERS is only supported with GCC and Clang, not with MSVC or clang-cl")
    endif()
  endif()

  if(${PROJECT_NAME}_ENABLE_THREAD_SANITIZER)
    if(sanitizers_supported)
      target_compile_options(${target}
        INTERFACE
          $<BUILD_INTERFACE:-fsanitize=thread>
          $<BUILD_INTERFACE:-fno-omit-frame-pointer>
      )
      target_link_options(${target}
        INTERFACE
          $<BUILD_INTERFACE:-fsanitize=thread>
      )
    else()
      message(WARNING "${PROJECT_NAME}_ENABLE_THREAD_SANITIZER is only supported with GCC and Clang, not with MSVC or clang-cl")
    endif()
  endif()
endfunction()
