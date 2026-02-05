add_library(usermod_factorial INTERFACE)

target_sources(usermod_factorial INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/factorial.c
)

target_include_directories(usermod_factorial INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_factorial)
