from lib import batteryless_patch
from lib import gba_patch


def batteryless_patcher(rom_path: str, out_path: str) -> int:
    return batteryless_patch.patch(rom_path, out_path)

def sram_patcher(rom_path: str, out_path: str) -> int:
    return gba_patch.sram_patch(rom_path, out_path)


