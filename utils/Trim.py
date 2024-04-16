def align(rom_path: str, out_path: str, align_size: int = 16):
    with open(rom_path, "rb") as rom:
        rom_data = rom.read()
    print(f"Starting to align {rom_path} to {align_size}B.")
    if len(rom_data) % align_size:
        rom_data += (align_size - (len(rom_data) % align_size)) * b"\0"
    with open(out_path, "wb") as out:
        out.write(rom_data)


def trim(rom_path: str, out_path: str, align_size: int = 16):
    with open(rom_path, "rb") as rom:
        rom_data = rom.read()
    print(f"Starting to trim {rom_path}.")
    print(f"Size before trim: {len(rom_data)/1024/1024}MB.")
    if len(rom_data) % align_size:
        rom_data += (align_size - (len(rom_data) % align_size)) * b"\0"
    try:
        trim_data = rom_data[-align_size:]
        assert trim_data in [align_size * b"\x00", align_size * b"\xFF"]
        cur_trim = len(rom_data) - align_size
        while rom_data[cur_trim : cur_trim + align_size] == trim_data:
            cur_trim -= align_size
        rom_data = rom_data[: cur_trim + align_size]
        print(f"Size after trim: {len(rom_data)/1024/1024}MB.")
    except:
        print(f"Can't trim {rom_path} and it's not needed to be trimmed.")
    with open(out_path, "wb") as out:
        out.write(rom_data)
