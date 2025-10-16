# coding=utf-8
import dataclasses
import json
import os
import shutil
import typing

from . import Patcher
from . import HeaderReader
from . import EmulatorBuilder
from rom_builder import rom_builder
from .CheckSaveType import check_save_type


class BuildInfo(typing.NamedTuple):
    path: str
    type: str
    msg: str
    success: bool


def build_start(options: dict, argoptions: dict, gamelist: list):
    rom_out_dir = "game_patched"
    if os.path.isdir("./sram_ips"):
        ips_game_list = os.listdir("./sram_ips")
        for i in range(0, len(ips_game_list)):
            ips_game_list[i] = os.path.splitext(ips_game_list[i])[0]
    else:
        ips_game_list = list()
    emu_game_list = ["GMBC", "PNES"]
    game_json_file = list()
    if os.path.exists(f"./{rom_out_dir}"):
        shutil.rmtree(f"./{rom_out_dir}")
    os.makedirs(f"./{rom_out_dir}")
    for game in gamelist:
        file_name_full: str = os.path.basename(game["path"])
        file_name: str = os.path.splitext(file_name_full)[0]
        file_type: str = os.path.splitext(file_name_full)[1]
        game_json_elem: dict = dict()
        out_file = f"./{rom_out_dir}/" + file_name + ".gba"
        match file_type.lower():
            case ".gba":
                if (
                    HeaderReader.get_id(game["path"]) in ips_game_list
                ):  # Some games can't be patched with the normal SRAM patch so use special ips patches for them.
                    if (
                        Patcher.ips_patcher(
                            game["path"],
                            "./sram_ips/" + HeaderReader.get_id(game["path"]) + ".ips",
                            out_file,
                        )
                        == 1
                    ):
                        yield BuildInfo(
                            file_name_full, "IPS patch", "IPS patch failed.", False
                        )
                        continue
                    else:
                        yield BuildInfo(
                            file_name_full, "IPS patch", "IPS patch succeed.", True
                        )

                elif (
                    HeaderReader.get_id(game["path"]) in emu_game_list
                ):  # Skip game patch if it's emulator.
                    shutil.copy(game["path"], out_file)
                else:
                    save_type = check_save_type(game["path"])
                    if save_type in ['none', 'sram']:
                        shutil.copy(game["path"], out_file)
                    elif Patcher.sram_patcher_bank(game["path"], out_file, argoptions["sram_bank_type"]) == 1:
                        yield BuildInfo(
                            file_name_full, "SRAM patch", "SRAM patch failed.", False
                        )
                        continue
                    else:
                        yield BuildInfo(
                            file_name_full, "SRAM patch", "SRAM patch succeed.", True
                        )
                if (
                    not options["battery_present"]
                    and game["save_slot"] is not None
                    and HeaderReader.get_id(game["path"]) not in emu_game_list
                ):
                    if Patcher.batteryless_patcher(out_file, out_file) == 2:
                        yield BuildInfo(
                            file_name_full,
                            "batteryless patch",
                            "Batteryless patch failed.",
                            False,
                        )
                        continue
                    else:
                        yield BuildInfo(
                            file_name_full,
                            "batteryless patch",
                            "Batteryless patch succeed.",
                            True,
                        )
            case ".gb" | ".gbc":
                if not options["battery_present"] and game["save_slot"] is not None:
                    EmulatorBuilder.build_goomba(
                        game["path"],
                        out_file,
                        goomba_path="./emulator/jagoombacolor_batteryless.gba",
                    )
                else:
                    EmulatorBuilder.build_goomba(game["path"], out_file)
                yield BuildInfo(
                    file_name_full, "goomba build", "Goomba build succeed.", True
                )
            case ".nes":
                if not options["battery_present"] and game["save_slot"] is not None:
                    EmulatorBuilder.build_pocketnes(
                        game["path"],
                        out_file,
                        pocketnes_path="./emulator/pocketnes_batteryless.gba",
                    )
                else:
                    EmulatorBuilder.build_pocketnes(game["path"], out_file)
                yield BuildInfo(
                    file_name_full, "pocketnes build", "PocketNES build succeed.", True
                )
            case _:
                print(game)
                print("Not acceptable")
                yield BuildInfo(
                    file_name_full, "type detect", "Not a valid type.", False
                )
                continue
        game_json_elem = {
            "enabled": True,  # Who would add a game in the GUI but disable it?
            "file": file_name + ".gba",
            "title": str(game["name"]),
            "title_font": 1,
            "save_slot": game["save_slot"],
        }
        game_json_file.append(game_json_elem)
    fin_json = {"cartridge": options, "games": game_json_file}
    json_file = open("./builder.json", "w", encoding="UTF-8-SIG")
    json_file.write(json.dumps(obj=fin_json, indent=4, ensure_ascii=False))
    json_file.close()

    build_config: rom_builder.Args = rom_builder.Args()
    build_config.cli_mode = False
    build_config.no_wait = True
    build_config.no_log = True
    build_config.config = "builder.json"
    build_config.rom_base_path = rom_out_dir
    if "bg" in argoptions.keys():
        build_config.bg = argoptions["bg"]
    if "split" in argoptions.keys():
        build_config.split = argoptions["split"]
    if "output" in argoptions.keys():
        build_config.output = argoptions["output"]
    build_result: rom_builder.FuncModeRet = rom_builder.build(
        dataclasses.asdict(build_config)
    )
    if build_result.success:
        if not build_result.data:
            yield BuildInfo(
                build_config.output, "multimenu build", "Multimenu build success.", True
            )
        else:
            yield BuildInfo(
                build_config.output,
                "multimenu build",
                f"Multimenu build success but the following games are not included because not enough space on the cartridge: {', '.join(map(lambda g:g["title"],build_result.data))}.",
                False,
            )
    else:
        yield BuildInfo(
            build_config.output,
            "multimenu build",
            f"Multimenu build failure, reason: {build_result.msg}.",
            False,
        )
