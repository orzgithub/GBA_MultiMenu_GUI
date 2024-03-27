# coding=utf-8

import os
import struct
import zlib


def build_goomba(
    rom_path: str | list[str], out_path: str, goomba_path="./emulator/jagoombacolor.gba"
):
    rom_path_list = [rom_path] if isinstance(rom_path, str) else rom_path
    goomba_file = open(goomba_path, "rb")
    build_rom = goomba_file.read()
    for rom_path in rom_path_list:
        with open(rom_path, "rb") as rom:
            build_rom += rom.read()
    with open(out_path, "wb") as final_file:
        final_file.write(build_rom)


def build_pocketnes(
    rom_path: str | list[str],
    out_path: str,
    pocketnes_path="./emulator/pocketnes.gba",
    romdata_db="./emulator/pnesmmw.mdb",
):
    rom_path_list = [rom_path] if isinstance(rom_path, str) else rom_path
    pocketnes_file = open(pocketnes_path, "rb")
    build_rom = pocketnes_file.read()
    size_emu_header = 0x30
    size_nes_header = (
        0x10  # len(b"NES\x1a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
    )
    build_rom += b"\0" * (
        (256 - ((len(build_rom) + size_emu_header + size_nes_header) % 256)) % 256
    )
    romdata_db_file = open(romdata_db, "r")
    for rom_path in rom_path_list:
        title = ""
        flag = 0
        deffollow = 0
        with open(rom_path, "rb") as rom:
            romdata = rom.read()
            romdata_no_header = (
                romdata[size_nes_header:] if romdata[0:4] == b"NES\x1a" else romdata
            )  # some rom dump doesn't contain a header
            rom_crc = str(hex(zlib.crc32(romdata_no_header)))[2:]
            in_db = False
            for line in romdata_db_file.readline():
                if "|" in line:
                    record = line.split("|")
                    if rom_crc == record[0]:
                        in_db = True
                        title = record[1]
                        if len(record) > 2:
                            if record[2] != "\n":
                                flag = int(record[2].split(" ")[0])
                            if len(record) > 3:
                                if record[3] != "\n":
                                    deffollow = int(record[3].split(" ")[0])
                    break
            if not in_db:
                title_text = os.path.splitext(os.path.basename(rom_path))[0]
                title = title_text.encode()
                if (
                    "(E)" in title_text
                    or "(Europe)" in title_text
                    or "(EUR)" in title_text
                ):
                    flag = flag | (1 << 2)
            title = title[:31]

            fin_rom = romdata + (
                b"\0" * ((256 - ((len(romdata) + size_emu_header) % 256)) % 256)
            )

            header = struct.pack("<31sx4I", title, len(fin_rom), flag, deffollow, 0)

            build_rom += header + fin_rom

    with open(out_path, "wb") as final_file:
        final_file.write(build_rom)
