add_library(usermod_container_attrs INTERFACE)

target_sources(usermod_container_attrs INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/container_attrs.c
)

target_include_directories(usermod_container_attrs INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_container_attrs)
