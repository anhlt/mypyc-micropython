add_library(usermod_class_param INTERFACE)

target_sources(usermod_class_param INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/class_param.c
)

target_include_directories(usermod_class_param INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_class_param)
