add_library(usermod_inventory INTERFACE)

target_sources(usermod_inventory INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/inventory.c
)

target_include_directories(usermod_inventory INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_inventory)
