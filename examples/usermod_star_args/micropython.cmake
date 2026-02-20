add_library(usermod_star_args INTERFACE)

target_sources(usermod_star_args INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/star_args.c
)

target_include_directories(usermod_star_args INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_star_args)
