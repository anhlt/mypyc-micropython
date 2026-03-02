add_library(usermod_sensor_lib INTERFACE)

target_sources(usermod_sensor_lib INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/sensor_lib.c
)

target_include_directories(usermod_sensor_lib INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_sensor_lib)
