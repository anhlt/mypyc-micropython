add_library(usermod_super_calls INTERFACE)

target_sources(usermod_super_calls INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/super_calls.c
)

target_include_directories(usermod_super_calls INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_super_calls)
