#!/bin/bash

# Designed on ArchLinux, x86_64. Mot guaranteed to work on other platforms.

CC=clang++
#Or changing it to g++ if you wish to build it with gcc.

$CC -O3 -Wall -shared -std=c++11 -fPIC $(python3 -m pybind11 --includes) src/*.cpp -o ../lib/gba_patch$(python3-config --extension-suffix) -lboost_filesystem
