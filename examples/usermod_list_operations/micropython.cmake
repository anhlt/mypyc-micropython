add_library(usermod_list_operations INTERFACE)

target_sources(usermod_list_operations INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/list_operations.c
)

target_include_directories(usermod_list_operations INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_list_operations)
