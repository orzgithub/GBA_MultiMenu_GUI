# GBA Multi Game Menu  GUI

This is a menu program to be run on Game Boy Advance bootleg cartridges which are equipped with a special multi-game
mapper.

Designed to work with lesserkuma's GBA Multi Game Menu.

This application can patch the game with SRAM patch and batteryless patch automatically so no extra operation needed
now. Just select the original ROM (Patched ROMs are ok. In most cases it won't be patched again.) in the GUI and
everything would be done.

## How to build

As this program is using C extensions you need to build these extensions to make it work.

You need to have gcc or clang, cmake, devkitarm for gba, pybind11, python and boost installed.

On linux or some simular *nix platforms you can execute the following commands:

```shell
export DEVKITPRO=<PATH_TO_DEVKITPRO>
export DEVKITARM=<PATH_TO_DEVKITARM>
cd batteryless_patch
cmake .
# make payload
# The source code has a pre-built payload_bin.hpp so no need to build it again. Uncommitt it if you wish to build it on your own.
make
cp batteryless_patch$(python3-config --extension-suffix) ../lib
cd ..
cd gba_patch
cmake .
make
cp gba_patch$(python3-config --extension-suffix) ../lib
cd ..
```

You can also build it on windows but it's impossible to built with msvc without some works on batteryless patcher. So
use msys2 toolchains instead.

This application also works for pypy and may other implements of python. But by default cmake would build it with
cpython so you may need to make some changes on CMakeLists.txt.

If everything goes right it should work. Just MultiMenuGUI_tkinter.py like other python applications (Of course you need
to install dependencies first and it's recommend to setup a venv.).

Or you can build it with Nuitka or pack it with pyinstaller. Additional files like bg.png, lk_multimenu.gba won't be
packed together with the final executable file so copy them together manually. Due to some limitations on nuitka,
config.json should also be placed with executable before starting it, while it would be generated with default config
automatically if you run it directly or packed by pyinstaller.

## Thanks

[GBA Multi Game Menu](https://github.com/lesserkuma/GBA_MultiMenu) By [lesserkuma](https://github.com/lesserkuma)

Used to build the menu.

[Batteryless Patch](https://github.com/metroid-maniac/gba-auto-batteryless-patcher)
By [metroid maniac](https://github.com/metroid-maniac)

Used to patch the game with batteryless patch.

[EZGBA](https://gbatemp.net/threads/release-ezgba-v0-1-0a-an-ez4-compatible-rom-patcher.395464/)
By [foobar_](https://gbatemp.net/members/foobar_.347556/)

Used to patch the game with SRAM patch.

[JaGoomba Color](https://github.com/EvilJagaGenius/jagoombacolor) By [EvilJagaGenius](https://github.com/EvilJagaGenius)
and [it's fork](https://github.com/lesserkuma/jagoombacolor) By [lesserkuma](https://github.com/lesserkuma)

Used to pack gb and gbc roms.

[PocketNES](https://github.com/Dwedit/PocketNES) By [Dwedit](https://github.com/Dwedit)
and [it's fork](https://github.com/lesserkuma/PocketNES) By [lesserkuma](https://github.com/lesserkuma)

Used to pack nes roms.
