add_library(usermod_lvgl INTERFACE)

target_sources(usermod_lvgl INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/lvgl.c
    ${CMAKE_CURRENT_LIST_DIR}/st7789_driver.c
)

file(GLOB_RECURSE LVGL_SOURCES
    ${CMAKE_CURRENT_LIST_DIR}/../../deps/lvgl/src/*.c
)

target_sources(usermod_lvgl INTERFACE ${LVGL_SOURCES})

target_include_directories(usermod_lvgl INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/../../deps/lvgl
    ${CMAKE_CURRENT_LIST_DIR}/../../deps/lvgl/src
)

target_compile_definitions(usermod_lvgl INTERFACE
    LV_CONF_INCLUDE_SIMPLE
)

if(IDF_TARGET)
    target_link_libraries(usermod_lvgl INTERFACE
        idf::driver
        idf::esp_lcd
        idf::esp_timer
        idf::heap
    )
endif()

# Suppress unused function/variable warnings for generated wrapper code
target_compile_options(usermod_lvgl INTERFACE
    -Wno-unused-function
    -Wno-unused-const-variable
)

target_link_libraries(usermod INTERFACE usermod_lvgl)
