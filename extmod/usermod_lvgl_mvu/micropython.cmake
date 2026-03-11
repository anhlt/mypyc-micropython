add_library(usermod_lvgl_mvu INTERFACE)

target_sources(usermod_lvgl_mvu INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/lvgl_mvu.c
)

target_include_directories(usermod_lvgl_mvu INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_options(usermod_lvgl_mvu INTERFACE
    -Wno-error=unused-variable
    -Wno-error=unused-function
    -Wno-error=unused-const-variable
)

target_link_libraries(usermod INTERFACE usermod_lvgl_mvu)
