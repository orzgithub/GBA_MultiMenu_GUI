# coding=utf-8

from lib import batteryless_patch
from lib import gba_patch

import locale


def batteryless_patcher(
    rom_path: str, out_path: str
) -> int:  # 0: Done 1: Failed but ok 2: Failed and broken
    print(end="")  # To make the patch result show in terminal at once.
    return batteryless_patch.patch(
        rom_path.encode(locale.getpreferredencoding()),
        out_path.encode(locale.getpreferredencoding()),
    )


def sram_patcher(rom_path: str, out_path: str) -> int:  # 0: Done 1: Failed
    print(end="")
    return gba_patch.sram_patch(
        rom_path.encode(locale.getpreferredencoding()),
        out_path.encode(locale.getpreferredencoding()),
    )


def ips_patcher(
    rom_path: str, ips_path: str, out_path: str
) -> int:  # 0: Done 1: Failed
    print(end="")
    return gba_patch.ips_patch(
        rom_path.encode(locale.getpreferredencoding()),
        ips_path.encode(locale.getpreferredencoding()),
        out_path.encode(locale.getpreferredencoding()),
    )
