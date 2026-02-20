add_library(usermod_print_test INTERFACE)

target_sources(usermod_print_test INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/print_test.c
)

target_include_directories(usermod_print_test INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_print_test)
