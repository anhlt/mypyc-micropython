add_library(usermod_default_args INTERFACE)

target_sources(usermod_default_args INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/default_args.c
)

target_include_directories(usermod_default_args INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_default_args)
