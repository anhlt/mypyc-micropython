add_library(usermod_set_operations INTERFACE)

target_sources(usermod_set_operations INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/set_operations.c
)

target_include_directories(usermod_set_operations INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_set_operations)
