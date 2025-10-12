def check_save_type(rom_path: str):
    PATTERNS = [
        (b"FLASH1M_V1", "flash1m"), # FLASH1M_V102 FLASH1M_V103
        (b"EEPROM_V1", "eeprom"), # EEPROM_V111 EEPROM_V120 EEPROM_V121 EEPROM_V122 EEPROM_V124 EEPROM_V126
        (b"FLASH_V1", "flash"), # FLASH_V120 FLASH_V121 FLASH_V123 FLASH_V124 FLASH_V125 FLASH_V126
        (b"FLASH512_V1", "flash"), # FLASH512_V130 FLASH512_V131 FLASH512_V133
        (b"SRAM_V1", "sram"), # SRAM_V110 SRAM_V111 SRAM_V112 SRAM_V113
        (b"SRAM_F_V1", "sram"), # SRAM_F_V100 SRAM_F_V102 SRAM_F_V103 SRAM_F_V110
    ]

    try:
        with open(rom_path, "rb") as f:
            rom_data = f.read()

        rom_view = memoryview(rom_data)

        for pattern, save_type in PATTERNS:
            if rom_view.find(pattern) != -1:
                return save_type

        return "none"

    except Exception:
        return "none"