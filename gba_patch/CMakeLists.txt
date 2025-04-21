cmake_minimum_required(VERSION 3.20)
project(gba_patch LANGUAGES CXX)

if(POLICY CMP0057)
	cmake_policy(SET CMP0057 NEW)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -Wall -fPIC")

find_package(Boost COMPONENTS filesystem REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)

file(GLOB sources ${PROJECT_SOURCE_DIR}/src/*.cpp ${PROJECT_SOURCE_DIR}/src/*.hpp)
pybind11_add_module(gba_patch ${sources})
target_link_libraries(gba_patch PRIVATE ${Boost_LIBRARIES})
