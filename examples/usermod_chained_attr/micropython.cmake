add_library(usermod_chained_attr INTERFACE)

target_sources(usermod_chained_attr INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/chained_attr.c
)

target_include_directories(usermod_chained_attr INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_chained_attr)
