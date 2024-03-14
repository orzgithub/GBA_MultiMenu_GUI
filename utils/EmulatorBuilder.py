def build_goomba(
    rom_path: str | list[str], out_path: str, goomba_path="emulator/jagoombacolor.gba"
):
    rom_path_list = [rom_path] if isinstance(rom_path, str) else rom_path
    goomba_file = open(goomba_path, "rb")
    build_rom = goomba_file.read()
    for rom_path in rom_path_list:
        with open(rom_path, "rb") as rom:
            build_rom += rom.read()
    with open(out_path, "wb") as final_file:
        final_file.write(build_rom)
