# coding=utf-8

from lib import batteryless_patch_rs


def batteryless_patcher(
    rom_path: str, out_path: str, auto_mode: bool
) -> int:  # 0: Done 1: Failed but ok 2: Failed and broken
    print(end="")  # To make the patch result show in terminal at once.
    return batteryless_patch_rs.patch(
        rom_path,
        out_path,
        auto_mode,
    )
