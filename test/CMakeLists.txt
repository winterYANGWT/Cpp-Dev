add_executable(${PROJECT_NAME}_test
  ${PROJECT_NAME}_test.cc
)

target_link_libraries(${PROJECT_NAME}_test
  PRIVATE
    ${PROJECT_NAME}::${PROJECT_NAME}
)

add_test(NAME ${PROJECT_NAME}_test COMMAND ${PROJECT_NAME}_test)
