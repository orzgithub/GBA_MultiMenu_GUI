#!/bin/bash

# Designed on ArchLinux, x86_64. Mot guaranteed to work on other platforms.

DEVKITPRO=/opt/devkitpro
DEVKITARM=$DEVKITPRO/devkitARM
CC=clang++
#Or changing it to g++ if you wish to build it with gcc.

$DEVKITARM/bin/arm-none-eabi-gcc -mcpu=arm7tdmi -nostartfiles -nodefaultlibs -mthumb -fPIE -Os -fno-toplevel-reorder src_payload/payload.c -T src_payload/payload.ld -o payload.elf
$DEVKITARM/bin/arm-none-eabi-objcopy -O binary payload.elf payload.bin
xxd -i payload.bin > src/payload_bin.cpp
$CC -O3 -Wall -shared -std=c++11 -fPIC $(python3 -m pybind11 --includes) src/*.cpp -o ../lib/batteryless_patch$(python3-config --extension-suffix)
