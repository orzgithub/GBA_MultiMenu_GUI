def align(rom_path: str, out_path: str):
    with open(rom_path, "rb") as rom:
        rom_data = rom.read()
    if len(rom_data) % 16:
        rom_data += (16 - (len(rom_data) % 16)) * b"\0"
    with open(out_path, "wb") as out:
        out.write(rom_data)


def trim(rom_path: str, out_path: str):
    with open(rom_path, "rb") as rom:
        rom_data = rom.read()
    if len(rom_data) % 16:
        rom_data += (16 - (len(rom_data) % 16)) * b"\0"
    try:
        trim_data = rom_data[-16:]
        assert trim_data in [16 * b"\x00", 16 * b"\xFF"]
        cur_trim = len(rom_data) - 16
        while rom_data[cur_trim : cur_trim + 16] == trim_data:
            cur_trim -= 16
        rom_data = rom_data[: cur_trim + 16]
    except:
        pass
    with open(out_path, "wb") as out:
        out.write(rom_data)
