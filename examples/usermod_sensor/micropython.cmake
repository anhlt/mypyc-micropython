add_library(usermod_sensor INTERFACE)

target_sources(usermod_sensor INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/sensor.c
)

target_include_directories(usermod_sensor INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_sensor)
