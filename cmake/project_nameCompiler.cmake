function(project_name_configure_cxx_target target)
  set_target_properties(${target} PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
  )

  target_compile_options(${target}
    PRIVATE
      $<$<CXX_COMPILER_ID:MSVC>:/W4>
      $<$<CXX_COMPILER_ID:MSVC>:/permissive->
      $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall>
      $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wextra>
      $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wpedantic>
  )

  if(${PROJECT_NAME}_WARNINGS_AS_ERRORS)
    target_compile_options(${target}
      PRIVATE
        $<$<CXX_COMPILER_ID:MSVC>:/WX>
        $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Werror>
    )
  endif()

  if(${PROJECT_NAME}_ENABLE_SANITIZERS)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
      target_compile_options(${target}
        PRIVATE
          -fsanitize=address,undefined
          -fno-omit-frame-pointer
      )
      target_link_options(${target}
        PRIVATE
          -fsanitize=address,undefined
      )
    else()
      message(WARNING "${PROJECT_NAME}_ENABLE_SANITIZERS is only supported with GCC and Clang")
    endif()
  endif()
endfunction()

function(project_name_configure_cxx_interface_target target)
  target_compile_features(${target}
    INTERFACE
      cxx_std_20
  )

  target_compile_options(${target}
    INTERFACE
      $<BUILD_INTERFACE:$<$<CXX_COMPILER_ID:MSVC>:/std:c++20>>
      $<BUILD_INTERFACE:$<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-std=c++20>>
      $<BUILD_INTERFACE:$<$<CXX_COMPILER_ID:MSVC>:/W4>>
      $<BUILD_INTERFACE:$<$<CXX_COMPILER_ID:MSVC>:/permissive->>
      $<BUILD_INTERFACE:$<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall>>
      $<BUILD_INTERFACE:$<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wextra>>
      $<BUILD_INTERFACE:$<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wpedantic>>
  )

  if(${PROJECT_NAME}_WARNINGS_AS_ERRORS)
    target_compile_options(${target}
      INTERFACE
        $<BUILD_INTERFACE:$<$<CXX_COMPILER_ID:MSVC>:/WX>>
        $<BUILD_INTERFACE:$<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Werror>>
    )
  endif()

  if(${PROJECT_NAME}_ENABLE_SANITIZERS)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
      target_compile_options(${target}
        INTERFACE
          $<BUILD_INTERFACE:-fsanitize=address,undefined>
          $<BUILD_INTERFACE:-fno-omit-frame-pointer>
      )
      target_link_options(${target}
        INTERFACE
          $<BUILD_INTERFACE:-fsanitize=address,undefined>
      )
    else()
      message(WARNING "${PROJECT_NAME}_ENABLE_SANITIZERS is only supported with GCC and Clang")
    endif()
  endif()
endfunction()
