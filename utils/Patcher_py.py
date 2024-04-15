# coding=utf-8

from gba_patch_py.patch import apply_ips_patch, patch_complement_check


def ips_patcher(
    rom_path: str, ips_path: str, out_path: str
) -> int:  # 0: Done 1: Failed
    print("Reading ROM file: " + rom_path)
    try:
        rom_data = open(rom_path, "rb").read()
    except Exception as e:
        print("Error reading ROM file.")
        print(e)
        return 1

    print("Reading IPS patch: " + ips_path)
    try:
        ips_data = open(ips_path, "rb").read()
    except Exception as e:
        print("Error reading IPS patch file.")
        print(e)
        return 1

    print("Applying IPS patch.")
    try:
        out_data = apply_ips_patch(rom_data, ips_data)
    except Exception as e:
        print("Failed to apply IPS patch.")
        print(e)
        return 1

    print("Correcting complement checksum.")
    try:
        out_data = patch_complement_check(out_data)
    except Exception as e:
        print("Error during complement check patch.")
        print(e)
        return 1

    print("Writing output file: " + out_path)
    try:
        with open(out_path, "wb") as out_file:
            out_file.write(out_data)
    except Exception as e:
        print("Failed to write file.")
        print(e)
        return 1
    return 0
