# coding=utf-8


def get_id(rom_path: str) -> str:
    with open(rom_path, "rb") as rom:
        rom.seek(0x00AC)
        id = rom.read(0x4).decode()
    return id


def get_name(rom_path: str) -> str:
    with open(rom_path, "rb") as rom:
        rom.seek(0x00A0)
        name = rom.read(0xC).decode().replace(b"\x00".decode(), " ").lstrip()
    return name


def get_version(rom_path: str) -> bytes:
    with open(rom_path, "rb") as rom:
        rom.seek(0x00BC)
        version = rom.read()
    return version
