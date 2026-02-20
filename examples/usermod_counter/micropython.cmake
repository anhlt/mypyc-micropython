add_library(usermod_counter INTERFACE)

target_sources(usermod_counter INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/counter.c
)

target_include_directories(usermod_counter INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_counter)
