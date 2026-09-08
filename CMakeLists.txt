cmake_minimum_required(VERSION 3.20)
project(parametric_closure_forests LANGUAGES CXX C)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(pcf
    src/instance.cpp
    src/pac.cpp
    src/dpac.cpp
    src/hpac.cpp
    src/hpac_eager.cpp
    src/hpac_bounded.cpp
    src/dhpac.cpp
    src/hipac.cpp
    src/hopac.cpp
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

# Hochbaum's fully parametric HPF solver, the comparison baseline: given only
# a parameter range it computes every breakpoint itself, so it solves the same
# problem HPaC does and can be raced against it directly. Vendored with its
# licence and a patch of two printf formats only -- see
# third_party/fphpf/UPSTREAM_README.md. Never linked into libpcf.
add_executable(pcf_fphpf third_party/fphpf/c/hpf.c third_party/fphpf/core/libhpf.c)
target_link_libraries(pcf_fphpf PRIVATE m)
