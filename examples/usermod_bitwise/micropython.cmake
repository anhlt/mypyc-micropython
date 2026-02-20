add_library(usermod_bitwise INTERFACE)

target_sources(usermod_bitwise INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/bitwise.c
)

target_include_directories(usermod_bitwise INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_bitwise)
