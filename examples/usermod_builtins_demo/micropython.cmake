add_library(usermod_builtins_demo INTERFACE)

target_sources(usermod_builtins_demo INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/builtins_demo.c
)

target_include_directories(usermod_builtins_demo INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_builtins_demo)
