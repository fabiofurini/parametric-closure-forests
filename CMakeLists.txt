cmake_minimum_required(VERSION 3.20)
project(parametric_closure_forests LANGUAGES CXX C)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(pcf
    src/instance.cpp
    src/fma.cpp
    src/dfma.cpp
    src/hfma.cpp
    src/dhfma.cpp
    src/hima.cpp
    src/homa.cpp
    src/rac.cpp
)
target_include_directories(pcf PUBLIC include PRIVATE src)
target_compile_options(pcf PRIVATE -Wall -Wextra -Wpedantic)

add_executable(pcf_solve src/cli.cpp)
target_link_libraries(pcf_solve PRIVATE pcf)

add_executable(pcf_tests tests/test_main.cpp)
target_link_libraries(pcf_tests PRIVATE pcf)
add_test(NAME pcf_tests COMMAND pcf_tests)

find_package(Git QUIET)
if(GIT_FOUND)
    execute_process(
        COMMAND ${GIT_EXECUTABLE} rev-parse --short=12 HEAD
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        OUTPUT_VARIABLE PCF_GIT_COMMIT
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
    )
endif()
if(NOT PCF_GIT_COMMIT)
    set(PCF_GIT_COMMIT "unknown")
endif()

add_executable(pcf_benchmark src/benchmark.cpp)
target_link_libraries(pcf_benchmark PRIVATE pcf)
target_compile_definitions(pcf_benchmark PRIVATE PCF_GIT_COMMIT="${PCF_GIT_COMMIT}")

add_executable(pcf_bppf third_party/bppf/pseudopar.c)
target_link_libraries(pcf_bppf PRIVATE m)
