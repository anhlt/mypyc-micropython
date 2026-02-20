add_library(usermod_tuple_operations INTERFACE)

target_sources(usermod_tuple_operations INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/tuple_operations.c
)

target_include_directories(usermod_tuple_operations INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_tuple_operations)
