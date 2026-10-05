cmake_minimum_required(VERSION 3.25)

project(ch09c_eq64_cpp_packet_export_v1 LANGUAGES CXX)

find_package(Python 3.12 COMPONENTS Interpreter Development REQUIRED)

execute_process(
    COMMAND "${Python_EXECUTABLE}" -c
            "import sysconfig; print(sysconfig.get_path('purelib'))"
    OUTPUT_VARIABLE HGRAPH_PYTHON_PREFIX
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE HGRAPH_PYTHON_PREFIX_RESULT
)
if(NOT HGRAPH_PYTHON_PREFIX_RESULT EQUAL 0 OR HGRAPH_PYTHON_PREFIX STREQUAL "")
    message(FATAL_ERROR "Could not determine Python site-packages prefix")
endif()

list(APPEND CMAKE_PREFIX_PATH "${HGRAPH_PYTHON_PREFIX}")
file(GLOB HGRAPH_CONFIG_HINTS
    LIST_DIRECTORIES true
    "${HGRAPH_PYTHON_PREFIX}/lib*/cmake/hgraph"
)

find_package(hgraph CONFIG REQUIRED HINTS ${HGRAPH_CONFIG_HINTS})

add_executable(
    ch09c_eq64_cpp_packet_export_v1
    "${CMAKE_CURRENT_LIST_DIR}/../ch09c_cpp_packet_export_v1.cpp"
)

target_compile_features(
    ch09c_eq64_cpp_packet_export_v1
    PRIVATE cxx_std_23
)

target_link_libraries(
    ch09c_eq64_cpp_packet_export_v1
    PRIVATE hgraph::core
)

if(COMMAND hgraph_link_python_embedding)
    hgraph_link_python_embedding(ch09c_eq64_cpp_packet_export_v1)
endif()

if(MSVC)
    target_compile_options(
        ch09c_eq64_cpp_packet_export_v1
        PRIVATE /W4 /WX /permissive-
    )
else()
    target_compile_options(
        ch09c_eq64_cpp_packet_export_v1
        PRIVATE -Wall -Wextra -Werror -Wno-pedantic
    )
endif()
