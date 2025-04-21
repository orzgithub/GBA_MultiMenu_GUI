cmake_minimum_required(VERSION 3.20)
project(batteryless_patch LANGUAGES CXX)

if(POLICY CMP0057)
	cmake_policy(SET CMP0057 NEW)
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -Wall -fPIC")

if(NOT DEFINED ENV{DEVKITARM})
    message(FATAL_ERROR "not defined environment variable:DEVKITARM")
endif()

add_custom_target(
	payload
	COMMAND $ENV{DEVKITARM}/bin/arm-none-eabi-gcc -mcpu=arm7tdmi -nostartfiles -nodefaultlibs -mthumb -fPIE -Os -fno-toplevel-reorder ${PROJECT_SOURCE_DIR}/src_payload/payload.c -T ${PROJECT_SOURCE_DIR}/src_payload/payload.ld -o payload.elf
	COMMAND $ENV{DEVKITARM}/bin/arm-none-eabi-objcopy -O binary ${PROJECT_SOURCE_DIR}/payload.elf payload.bin
	COMMAND xxd -i payload.bin > ${PROJECT_SOURCE_DIR}/src/payload_bin.hpp
)

file(GLOB sources ${PROJECT_SOURCE_DIR}/src/*.cpp ${PROJECT_SOURCE_DIR}/src/*.h)
pybind11_add_module(batteryless_patch ${sources})
