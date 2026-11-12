# Adds the ${PROJECT_NAME}_docs target, which runs Doxygen on the public headers
# and writes HTML to ${PROJECT_BINARY_DIR}/doxygen/html. Doxygen warnings fail
# the target when ${PROJECT_NAME}_WARNINGS_AS_ERRORS is ON.
function(mylib_add_docs_target)
  find_package(Doxygen REQUIRED COMPONENTS doxygen)
  if(DOXYGEN_VERSION VERSION_LESS 1.13)
    message(WARNING
      "Doxygen ${DOXYGEN_VERSION} does not report undocumented namespaces, so "
      "it does not check the members of a namespace without documentation. "
      "Use Doxygen 1.13 or newer for a complete check."
    )
  endif()

  set(docs_input_dir "${PROJECT_SOURCE_DIR}/include")
  set(docs_output_dir "${PROJECT_BINARY_DIR}/doxygen")

  # Macros defined by generate_export_header().
  string(TOUPPER "${PROJECT_NAME}" macro_prefix)
  set(docs_predefined "")
  foreach(suffix IN ITEMS
      EXPORT NO_EXPORT DEPRECATED DEPRECATED_EXPORT DEPRECATED_NO_EXPORT)
    string(APPEND docs_predefined " ${macro_prefix}_${suffix}=")
  endforeach()
  string(STRIP "${docs_predefined}" docs_predefined)

  if(${PROJECT_NAME}_WARNINGS_AS_ERRORS)
    set(docs_warn_as_error FAIL_ON_WARNINGS)
  else()
    set(docs_warn_as_error NO)
  endif()

  configure_file(
    "${PROJECT_SOURCE_DIR}/docs/Doxyfile.in"
    "${PROJECT_BINARY_DIR}/Doxyfile"
    @ONLY
  )

  add_custom_target(${PROJECT_NAME}_docs
    COMMAND Doxygen::doxygen "${PROJECT_BINARY_DIR}/Doxyfile"
    WORKING_DIRECTORY "${PROJECT_BINARY_DIR}"
    COMMENT "Generating ${PROJECT_NAME} API documentation with Doxygen"
    VERBATIM
  )
endfunction()
