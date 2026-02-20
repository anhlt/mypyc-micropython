add_library(usermod_algorithms INTERFACE)

target_sources(usermod_algorithms INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/algorithms.c
)

target_include_directories(usermod_algorithms INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_algorithms)
