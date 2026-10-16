option(${PROJECT_NAME}_BUILD_TESTS "Build ${PROJECT_NAME} tests" ${PROJECT_IS_TOP_LEVEL})
option(${PROJECT_NAME}_INSTALL "Install ${PROJECT_NAME}" ${PROJECT_IS_TOP_LEVEL})
option(${PROJECT_NAME}_ENABLE_SANITIZERS "Build ${PROJECT_NAME} with AddressSanitizer and UndefinedBehaviorSanitizer" OFF)
option(${PROJECT_NAME}_ENABLE_THREAD_SANITIZER "Build ${PROJECT_NAME} with ThreadSanitizer" OFF)
option(${PROJECT_NAME}_WARNINGS_AS_ERRORS "Treat ${PROJECT_NAME} compiler warnings as errors" OFF)

if(${PROJECT_NAME}_ENABLE_SANITIZERS AND ${PROJECT_NAME}_ENABLE_THREAD_SANITIZER)
  message(FATAL_ERROR
    "${PROJECT_NAME}_ENABLE_SANITIZERS and ${PROJECT_NAME}_ENABLE_THREAD_SANITIZER "
    "cannot both be ON: ThreadSanitizer cannot be combined with AddressSanitizer."
  )
endif()
