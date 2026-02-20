add_library(usermod_string_operations INTERFACE)

target_sources(usermod_string_operations INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/string_operations.c
)

target_include_directories(usermod_string_operations INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_string_operations)
