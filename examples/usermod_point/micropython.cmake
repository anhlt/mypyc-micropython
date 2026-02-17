add_library(usermod_point INTERFACE)

target_sources(usermod_point INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/point.c
)

target_include_directories(usermod_point INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_point)
