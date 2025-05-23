# -*- coding: utf-8 -*-
# GBA Multi Game Menu – ROM Builder
# Author: Lesserkuma (github.com/lesserkuma)
import sys, os, glob, json, math, re, struct, hashlib, argparse, datetime, dataclasses, typing

# Configuration
app_version = "1.1"

################################


class FuncModeRet(typing.NamedTuple):
    msg: str
    data: dict | list | None
    success: bool


@dataclasses.dataclass
class Args:
    split: bool = False
    no_wait: bool = False
    no_log: bool = False
    config: str = "config.json"
    bg: str = "bg.png"
    output: str = "LK_MULTIMENU_<CODE>.gba"
    rom_base_path: str = "roms"
    cli_mode: bool = True


log = ""


def build(args_set: dict = None) -> FuncModeRet | int:
    args: Args = Args(**args_set)

    def UpdateSectorMap(start, length, c):
        sector_map[start + 1 : start + length] = c * (length - 1)
        sector_map[start] = c.upper()

    def formatFileSize(size):
        if size == 1:
            return "{:d} Byte".format(size)
        elif size < 1024:
            return "{:d} Bytes".format(size)
        elif size < 1024 * 1024:
            val = size / 1024
            return "{:.1f} KB".format(val)
        else:
            val = size / 1024 / 1024
            return "{:.2f} MB".format(val)

    def logp(*args, **kwargs):
        global log
        s = format(" ".join(map(str, args)))
        print("{:s}".format(s), **kwargs)
        if "end" in kwargs and kwargs["end"] == "":
            log += "{:s}".format(s)
        else:
            log += "{:s}\n".format(s)

    ################################

    cartridge_types = [
        {
            "name": "MSP55LV100S",
            "flash_size": 0x4000000,
            "sector_size": 0x20000,
            "block_size": 0x80000,
        },
        {
            "name": "6600M0U0BE",
            "flash_size": 0x10000000,
            "sector_size": 0x40000,
            "block_size": 0x80000,
        },
        {
            "name": "MSP54LV100",
            "flash_size": 0x8000000,
            "sector_size": 0x20000,
            "block_size": 0x80000,
        },
        {
            "name": "F0095H0",
            "flash_size": 0x20000000,
            "sector_size": 0x40000,
            "block_size": 0x80000,
        },
    ]
    now = datetime.datetime.now()

    logp("GBA Multi Game Menu ROM Builder v{:s}\nby Lesserkuma\n".format(app_version))

    output_file = args.output
    if output_file == "lk_multimenu.gba":
        logp("Error: The file must not be named “lk_multimenu.gba”")
        if not args.no_wait:
            input("\nPress ENTER to exit.\n")
        return 1 if args.cli_mode else FuncModeRet("Wrong output name.", None, False)
    if not os.path.exists("lk_multimenu.gba"):
        logp(
            "Error: The Menu ROM is missing.\nPlease put it in the same directory that you are running this tool from.\nExpected file name: “lk_multimenu.gba”"
        )
        if not args.no_wait:
            input("\nPress ENTER to exit.\n")
        return (
            0 if args.cli_mode else FuncModeRet("Couldn't found base rom.", None, False)
        )

    # Read game list
    files = []
    if not os.path.exists(args.config):
        files = glob.glob(args.rom_base_path + "/*.gba")
        files = sorted(files, key=str.casefold)
        save_slot = 1
        games = []
        cartridge_type = 1
        battery_present = False
        min_rom_size = 0x400000
        for file in files:
            d = {
                "enabled": True,
                "file": os.path.split(file)[1],
                "title": os.path.splitext(os.path.split(file)[1])[0],
                "title_font": 1,
                "save_slot": save_slot,
            }
            with open(file, "rb") as f:
                f.seek(0xAC)
                code = f.read(0x4)
                if code[:3] in (b"BPG", b"BPR"):
                    d["map_256m"] = True
            games.append(d)
            save_slot += 1
        obj = {
            "cartridge": {
                "type": cartridge_type + 1,
                "battery_present": battery_present,
                "min_rom_size": min_rom_size,
            },
            "games": games,
        }
        if len(games) == 0:
            logp(
                f"Error: No usable ROM files were found in the “{args.rom_base_path:s}” folder."
            )
        else:
            with open(args.config, "w", encoding="UTF-8-SIG") as f:
                f.write(json.dumps(obj=obj, indent=4, ensure_ascii=False))
            logp(
                f"A new configuration file ({args.config:s}) was created based on the files inside the “{args.rom_base_path:s}” folder.\nPlease edit the file to your liking in a text editor, then run this tool again."
            )
        if not args.no_wait:
            input("\nPress ENTER to exit.\n")
        return (
            0
            if args.cli_mode
            else FuncModeRet(
                f"Config {args.rom_base_path:s}/{args.config:s} generated.", None, True
            )
        )
    else:
        with open(args.config, "r", encoding="UTF-8-SIG") as f:
            try:
                j = json.load(f)
            except json.decoder.JSONDecodeError as e:
                logp(
                    f"Error: The configuration file ({args.config:s}) is malformed and could not be loaded.\n"
                    + str(e)
                )
                if not args.no_wait:
                    input("\nPress ENTER to exit.\n")
                return (
                    1
                    if args.cli_mode
                    else FuncModeRet(f"Config couldn't prease.", None, False)
                )
            games = j["games"]
            cartridge_type = j["cartridge"]["type"] - 1
            battery_present = j["cartridge"]["battery_present"]
            if "min_rom_size" in j["cartridge"]:
                min_rom_size = j["cartridge"]["min_rom_size"]
            else:
                min_rom_size = 0x400000

    # Prepare compilation
    flash_size = cartridge_types[cartridge_type]["flash_size"]
    sector_size = cartridge_types[cartridge_type]["sector_size"]
    sector_count = flash_size // sector_size
    block_size = cartridge_types[cartridge_type]["block_size"]
    block_count = flash_size // block_size
    sectors_per_block = 0x80000 // sector_size
    compilation = bytearray()
    roms_keys = [0]
    for i in range(flash_size // 0x2000000):
        chunk = bytearray([0xFF] * 0x2000000)
        compilation += chunk
    sector_map = list("." * sector_count)

    # Read menu ROM
    with open("lk_multimenu.gba", "rb") as f:
        menu_rom = bytearray(f.read())
        menu_rom += bytearray(
            [0xFF] * ((len(menu_rom) + 0x10 - (len(menu_rom) % 0x10)) - len(menu_rom))
        )
        menu_rom += bytearray([0xFF] * 0x20)
        build_timestamp_offset = len(menu_rom) - 0x20
        build_timestamp = (
            datetime.datetime.now()
            .astimezone()
            .replace(microsecond=0)
            .isoformat()
            .encode("ASCII")
        )
        menu_rom[
            build_timestamp_offset : build_timestamp_offset + len(build_timestamp)
        ] = build_timestamp

    # Change background image
    if args.bg != Args.bg or os.path.exists("bg.png"):
        try:
            from PIL import Image

            if args.bg:
                img = Image.open(args.bg)
            else:
                img = Image.open("bg.png")
            img = img.convert("P")
            palette = img.getpalette()
            palette_rgb555 = [
                ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)
                for r, g, b in zip(palette[::3], palette[1::3], palette[2::3])
            ]
            raw_bitmap = bytearray(list(img.tobytes()))
            raw_palette = bytearray(0x200)
            pos = 0
            for color in palette_rgb555:
                raw_palette[pos : pos + 2] = struct.pack("<H", color)
                pos += 2
            menu_rom_bg_offset = menu_rom.find(b"RTFN\xff\xfe") - 0x9800
            menu_rom[menu_rom_bg_offset : menu_rom_bg_offset + 0x9600] = raw_bitmap
            menu_rom[menu_rom_bg_offset + 0x9600 : menu_rom_bg_offset + 0x9800] = (
                raw_palette
            )
        except ImportError:
            print(
                "Error: Couldn’t update background image. Pillow library is not installed."
            )

    menu_rom_size = menu_rom.find(b"dkARM\0\0\0") + 8
    compilation[0 : len(menu_rom)] = menu_rom
    UpdateSectorMap(start=0, length=math.ceil(len(menu_rom) / sector_size), c="m")
    item_list_offset = len(menu_rom)
    item_list_offset = 0x40000 - (item_list_offset % 0x40000) + item_list_offset
    item_list_offset = math.ceil(item_list_offset / sector_size)
    UpdateSectorMap(start=item_list_offset, length=1, c="l")
    status_offset = item_list_offset + 1
    UpdateSectorMap(start=status_offset, length=1, c="c")
    if battery_present:
        status = bytearray(
            [
                0x4B,
                0x55,
                0x4D,
                0x41,
                0x00,
                0x01,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
            ]
        )
    else:
        status = bytearray(
            [
                0x4B,
                0x55,
                0x4D,
                0x41,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
            ]
        )
    compilation[
        status_offset * sector_size : status_offset * sector_size + len(status)
    ] = status
    save_data_sector_offset = status_offset + 1
    boot_logo_found = hashlib.sha1(compilation[0x04:0xA0]).digest() == bytearray(
        [
            0x17,
            0xDA,
            0xA0,
            0xFE,
            0xC0,
            0x2F,
            0xC3,
            0x3C,
            0x0F,
            0x6A,
            0xBB,
            0x54,
            0x9A,
            0x8B,
            0x80,
            0xB6,
            0x61,
            0x3B,
            0x48,
            0xEE,
        ]
    )

    # Read game ROMs and import save data
    saves_read = []
    games = [game for game in games if "enabled" in game and game["enabled"]]
    index = 0
    for game in games:
        if not game["enabled"]:
            continue
        if not os.path.exists(f"{args.rom_base_path:s}/{game['file']}"):
            game["missing"] = True
            continue
        size = os.path.getsize(f"{args.rom_base_path:s}/{game['file']}")
        if (size & (size - 1)) != 0:
            x = 0x80000
            while x < size:
                x *= 2
            size = x
        if size < 0x400000:
            with open(f"{args.rom_base_path:s}/{game['file']}", "rb") as f:
                buffer = f.read()
                if b"Batteryless mod by Lesserkuma" in buffer:
                    size = max(0x400000, min_rom_size)
                else:
                    size = max(size, min_rom_size)
        game["index"] = index
        game["size"] = size
        if "title_font" in game:
            game["title_font"] -= 1
        else:
            game["title_font"] = 0
        game["sector_count"] = int(size / sector_size)

        # Hidden ROMs
        keys = 0
        if "keys" in game:
            for key in game["keys"]:
                if key.upper() == "A":
                    keys |= 1 << 0
                elif key.upper() == "B":
                    keys |= 1 << 1
                elif key.upper() == "SELECT":
                    keys |= 1 << 2
                elif key.upper() == "START":
                    keys |= 1 << 3
                elif key.upper() == "RIGHT":
                    keys |= 1 << 4
                elif key.upper() == "LEFT":
                    keys |= 1 << 5
                elif key.upper() == "UP":
                    keys |= 1 << 6
                elif key.upper() == "DOWN":
                    keys |= 1 << 7
                elif key.upper() == "R":
                    keys |= 1 << 8
                elif key.upper() == "L":
                    keys |= 1 << 9
        game["keys"] = keys

        if keys > 0:
            roms_keys.append(keys)
            roms_keys = list(set(roms_keys))

        if battery_present and game["save_slot"] is not None:
            game["save_type"] = 2
            game["save_slot"] -= 1
            save_slot = game["save_slot"]
            offset = save_data_sector_offset + save_slot
            UpdateSectorMap(offset, 1, "s")

            if save_slot not in saves_read:
                save_data_file = (
                    os.path.splitext(f"{args.rom_base_path:s}/{game['file']}")[0]
                    + ".sav"
                )
                save_data = bytearray([0] * sector_size)
                if os.path.exists(save_data_file):
                    with open(save_data_file, "rb") as f:
                        save_data = f.read()
                    if len(save_data) < sector_size:
                        save_data += bytearray([0] * (sector_size - len(save_data)))
                    if len(save_data) > sector_size:
                        save_data = save_data[:sector_size]
                    saves_read.append(save_slot)
                compilation[
                    offset * sector_size : offset * sector_size + sector_size
                ] = save_data
        else:
            game["save_type"] = 0
            game["save_slot"] = 0
        index += 1
    if len(saves_read) > 0:
        save_end_offset = "".join(sector_map).rindex("S") + 1
    else:
        save_end_offset = save_data_sector_offset

    games = [game for game in games if not ("missing" in game and game["missing"])]
    if len(games) == 0:
        logp(
            f"No ROMs found. Delete the “{args.config:s}” file to reset your configuration."
        )
        return (
            1
            if args.cli_mode
            else FuncModeRet(f"Some games in config missing.", None, False)
        )
    # Add index
    index = 0
    for game in games:
        game["index"] = index
        index += 1

    # Read ROM data
    games_not_found: list = []
    games.sort(key=lambda game: game["size"], reverse=True)
    for game in games:
        found = False
        for i in range(save_end_offset, len(sector_map)):
            sector_count_map = game["sector_count"]

            if "map_256m" in game and game["map_256m"] == True:
                # Map as 256M ROM, but don't waste space; some games may need this for unknown reasons
                sector_count_map = (32 * 1024 * 1024) // sector_size

            if i % sector_count_map == 0:
                if (
                    sector_map[i : i + game["sector_count"]]
                    == ["."] * game["sector_count"]
                ):
                    UpdateSectorMap(i, game["sector_count"], "r")
                    with open(f"{args.rom_base_path:s}/{game['file']}", "rb") as f:
                        rom = f.read()
                    compilation[i * sector_size : i * sector_size + len(rom)] = rom
                    game["sector_offset"] = i
                    game["block_offset"] = (
                        game["sector_offset"] * sector_size // block_size
                    )
                    game["block_count"] = sector_count_map * sector_size // block_size
                    found = True

                    if not boot_logo_found and hashlib.sha1(
                        rom[0x04:0xA0]
                    ).digest() == bytearray(
                        [
                            0x17,
                            0xDA,
                            0xA0,
                            0xFE,
                            0xC0,
                            0x2F,
                            0xC3,
                            0x3C,
                            0x0F,
                            0x6A,
                            0xBB,
                            0x54,
                            0x9A,
                            0x8B,
                            0x80,
                            0xB6,
                            0x61,
                            0x3B,
                            0x48,
                            0xEE,
                        ]
                    ):
                        compilation[0x04:0xA0] = rom[0x04:0xA0]  # boot logo
                        boot_logo_found = True
                    break
        if not found:
            games_not_found.append(game)
            logp(
                "“{:s}” couldn’t be added because it exceeds the available cartridge space.".format(
                    game["title"]
                )
            )

    if not boot_logo_found:
        logp("Warning: Valid boot logo is missing!")

    # Generate item list
    games = [game for game in games if "sector_offset" in game]
    games.sort(key=lambda game: game["index"])

    # Print information
    logp("Sector map (1 block = {:d} KiB):".format(sector_size // 1024))
    for i in range(0, len(sector_map)):
        logp(sector_map[i], end="")
        if i % 64 == 63:
            logp("")
    sectors_used = len(re.findall(r"[MmSsRrIiCc]", "".join(sector_map)))
    logp(
        "{:.2f}% ({:d} of {:d} sectors) used\n".format(
            sectors_used / sector_count * 100, sectors_used, sector_count
        )
    )
    logp(f"Added {len(games)} ROM(s) to the compilation\n")

    if battery_present:
        logp("    | Offset     | Map Size  | Save Slot      | Title")
        toc_sep = "----+------------+-----------+----------------+--------------------------------"
    else:
        logp("    | Offset     | Map Size  | Title")
        toc_sep = "----+------------+-----------+-------------------------------------------------"

    item_list = bytearray()

    for key in roms_keys:
        c = 0
        for game in games:
            if game["keys"] != key:
                continue

            title = game["title"]
            if len(title) > 0x30:
                title = title[:0x2F] + "…"

            table_line = (
                f"{game['index'] + 1:3d} | "
                + f"0x{game['block_offset'] * block_size:X} | ".rjust(13, " ")
                + f"0x{game['block_count'] * block_size:X} | ".rjust(12, " ")
            )
            if battery_present:
                if game["save_type"] > 0:
                    table_line += f"{game['save_slot']+1:2d} (0x{(save_data_sector_offset + game['save_slot']) * sector_size:07X}) | "
                else:
                    table_line += "               | "
            table_line += f"{title}"
            if c % 8 == 0:
                if game["keys"] != 0:
                    temp = toc_sep[:-9] + "[Hidden]-"
                    logp(temp)
                else:
                    logp(toc_sep)
            logp(table_line)
            c += 1

            title = title.ljust(0x30, "\0")
            item_list += bytearray(struct.pack("B", game["title_font"]))
            item_list += bytearray(struct.pack("B", len(game["title"])))
            item_list += bytearray(struct.pack("<H", game["block_offset"]))
            item_list += bytearray(struct.pack("<H", game["block_count"]))
            item_list += bytearray(struct.pack("B", game["save_type"]))
            item_list += bytearray(struct.pack("B", game["save_slot"]))
            item_list += bytearray(struct.pack("<H", game["keys"]))
            item_list += bytearray([0] * 6)
            item_list += bytearray(title.encode("UTF-16LE"))

    compilation[
        item_list_offset * sector_size : item_list_offset * sector_size + len(item_list)
    ] = item_list
    rom_code = "L{:s}".format(hashlib.sha1(status + item_list).hexdigest()[:3]).upper()

    # Write compilation
    rom_size = len("".join(sector_map).rstrip(".")) * sector_size
    compilation[0xAC:0xB0] = rom_code.encode("ASCII")
    checksum = 0
    for i in range(0xA0, 0xBD):
        checksum = checksum - compilation[i]
    checksum = (checksum - 0x19) & 0xFF
    compilation[0xBD] = checksum
    logp("")
    logp("Menu ROM:        0x{:08X}–0x{:08X}".format(0, len(menu_rom)))
    logp(
        "Game List:       0x{:08X}–0x{:08X}".format(
            item_list_offset * sector_size,
            item_list_offset * sector_size + len(item_list),
        )
    )
    logp(
        "Status Area:     0x{:08X}–0x{:08X}".format(
            status_offset * sector_size, status_offset * sector_size + 0x1000
        )
    )
    logp("")
    logp(
        "Cartridge Type:  {:d} ({:s}) {:s}".format(
            cartridge_type + 1,
            cartridge_types[cartridge_type]["name"],
            "with battery" if battery_present else "without battery",
        )
    )
    logp("Output ROM Size: {:.2f} MiB".format(rom_size / 1024 / 1024))
    logp("Output ROM Code: {:s}".format(rom_code))
    output_file = output_file.replace("<CODE>", rom_code)

    if args.split:
        for i in range(0, math.ceil(flash_size / 0x2000000)):
            pos = i * 0x2000000
            size = 0x2000000
            if pos > len(compilation[:rom_size]):
                break
            if pos + size > rom_size:
                size = rom_size - pos
            output_file_part = "{:s}_part{:d}{:s}".format(
                os.path.splitext(output_file)[0], i, os.path.splitext(output_file)[1]
            )
            with open(output_file_part, "wb") as f:
                f.write(compilation[pos : pos + size])
    else:
        with open(output_file, "wb") as f:
            f.write(compilation[:rom_size])

    # Write log
    if not args.no_log:
        global log
        log += "\nArgument List: {:s}\n".format(str(sys.argv[1:]))
        log += "\n################################\n\n"
        with open("log.txt", "ab") as f:
            f.write(log.encode("UTF-8-SIG"))
    if not args.no_wait:
        input("\nPress ENTER to exit.\n")
    return (
        0
        if args.cli_mode
        else FuncModeRet(
            f"Target rom generated.{" Some games failed to included." if games_not_found else ""}",
            games_not_found,
            True,
        )
    )


if __name__ == "__main__":

    class ArgParseCustomFormatter(
        argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
    ):
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split",
        help="splits output files into 32 MiB parts",
        action="store_true",
        default=Args.split,
    )
    parser.add_argument(
        "--no-wait",
        help="don’t wait for user input when finished",
        action="store_true",
        default=Args.no_wait,
    )
    parser.add_argument(
        "--no-log",
        help="don’t write a log file",
        action="store_true",
        default=Args.no_log,
    )
    parser.add_argument(
        "--config",
        type=str,
        default=Args.config,
        help="sets the config file to use",
    )
    parser.add_argument(
        "--bg",
        type=str,
        default=Args.bg,
        help="sets the background image to use",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=Args.output,
        help="sets the file name of the compilation ROM",
    )
    parser.add_argument(
        "--rom-base-path",
        type=str,
        default=Args.rom_base_path,
        help="sets the folder where the ROM stored",
    )

    args = parser.parse_args()
    ret = build(
        {
            "split": args.split,
            "no_wait": args.no_wait,
            "no_log": args.no_log,
            "config": args.config,
            "bg": args.bg,
            "output": args.output,
            "rom_base_path": args.rom_base_path,
            "cli_mode": True,
        }
    )
    if ret is not None and ret != 0:
        sys.exit(ret)
