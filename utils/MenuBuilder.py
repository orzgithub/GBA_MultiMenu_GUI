# coding=utf-8

import json
import os
import shutil

from utils import Patcher
from utils import HeaderReader
from utils import EmulatorBuilder
from rom_builder import rom_builder


def build_start(options: dict, argoptions: dict, gamelist: list):
    if os.path.isdir("./sram_ips"):
        ips_game_list = os.listdir("./sram_ips")
        for i in range(0, len(ips_game_list)):
            ips_game_list[i] = os.path.splitext(ips_game_list[i])[0]
    else:
        ips_game_list = list()
    emu_game_list = ["GMBC", "PNES"]
    game_json_file = list()
    if os.path.exists("./game_patched"):
        shutil.rmtree("./game_patched")
    os.makedirs("./game_patched")
    for game in gamelist:
        file_name_full: str = os.path.basename(game["path"])
        file_name: str = os.path.splitext(file_name_full)[0]
        file_type: str = os.path.splitext(file_name_full)[1]
        game_json_elem: dict = dict()
        out_file = "./game_patched/" + file_name + ".gba"
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
                        yield file_name_full, "IPS patch"
                        continue
                elif (
                    HeaderReader.get_id(game["path"]) in emu_game_list
                ):  # Skip game patch if it's emulator.
                    shutil.copy(game["path"], out_file)
                else:
                    if Patcher.sram_patcher(game["path"], out_file) == 1:
                        yield file_name_full, "SRAM patch"
                        continue
                if (
                    not options["battery_present"]
                    and game["save_slot"] is not None
                    and HeaderReader.get_id(game["path"]) not in emu_game_list
                ):
                    if Patcher.batteryless_patcher(out_file, out_file) == 2:
                        yield file_name_full, "batteryless patch"
                        continue
            case ".gb" | ".gbc":
                if not options["battery_present"] and game["save_slot"] is not None:
                    EmulatorBuilder.build_goomba(
                        game["path"],
                        out_file,
                        goomba_path="./emulator/jagoombacolor_batteryless.gba",
                    )
                else:
                    EmulatorBuilder.build_goomba(game["path"], out_file)
            case ".nes":
                if not options["battery_present"] and game["save_slot"] is not None:
                    EmulatorBuilder.build_pocketnes(
                        game["path"],
                        out_file,
                        pocketnes_path="./emulator/pocketnes_batteryless.gba",
                    )
                else:
                    EmulatorBuilder.build_pocketnes(game["path"], out_file)
            case _:
                print(game)
                print("Not acceptable")
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
    json_file = open("./builder.json", "w")
    json_file.write(json.dumps(obj=fin_json, indent=4, ensure_ascii=False))
    json_file.close()

    build_config: dict = rom_builder.args_dict_template.copy()
    build_config["no-wait"] = True
    build_config["no-log"] = True
    build_config["config"] = "builder.json"
    build_config["rom-base-path"] = "game_patched"
    if "bg" in argoptions.keys():
        build_config["bg"] = argoptions["bg"]
    if "split" in argoptions.keys():
        build_config["split"] = argoptions["split"]
    if "bg" in argoptions.keys():
        build_config["bg"] = argoptions["bg"]
    if "output" in argoptions.keys():
        build_config["output"] = argoptions["output"]
    rom_builder.build(build_config)
