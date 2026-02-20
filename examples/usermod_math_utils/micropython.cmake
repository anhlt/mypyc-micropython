add_library(usermod_math_utils INTERFACE)

target_sources(usermod_math_utils INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/math_utils.c
)

target_include_directories(usermod_math_utils INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_math_utils)
