import json
import os
import shutil

import Patcher
import rom_builder.rom_builder as rom_builder


def build_start(options: dict, argoptions: dict, gamelist: list):
    game_json_file = list()
    for game in gamelist:
        file_name = os.path.basename(game["path"])
        out_file = "./game_patched/" + file_name
        if game["save_slot"] is None:
            shutil.copy(game["path"], out_file)
        else:
            Patcher.sram_patcher(game["path"], out_file)
            if not options["battery_present"]:
                Patcher.batteryless_patcher(out_file, out_file)
        game_json_elem = {
            "enabled": True,  # Who would add a game in the GUI but disable it?
            "file": file_name,
            "title": game["name"],
            "title_font": 1,
            "save_slot": game["save_slot"],
        }
        game_json_file.append(game_json_elem)
    fin_json = {"cartridge": options, "games": game_json_file}
    json_file = open("builder.json", "w")
    json_file.write(json.dumps(fin_json))
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
    rom_builder.build(build_config)
