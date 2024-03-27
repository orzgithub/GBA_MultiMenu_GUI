from typing import Literal


def apply_ips_patch(rom_data: bytes, ips_data: bytes) -> bytes:
    if len(ips_data) > 5 and ips_data[:5] == b"PATCH":
        read_pos = 5
        while read_pos < len(ips_data):
            write_pos = 0
            write_size = 0
            rle_size = 0
            rle_value = 0x00
            if read_pos + 3 > len(ips_data):
                raise Exception(
                    "Insufficient bytes for offset reading (3 bytes) at IPS patch read position "
                    + str(read_pos)
                    + "."
                )
            else:
                if ips_data[read_pos : read_pos + 3] == b"EOF":
                    read_pos += 3
                    break
                else:
                    write_pos = read_bytes_to_value(ips_data, read_pos, 3)
                    read_pos += 3

            if read_pos + 2 > len(ips_data):
                raise Exception(
                    "Insufficient bytes for patch size reading (2 bytes) at IPS patch read position "
                    + str(read_pos)
                    + "."
                )
            else:
                write_size = read_bytes_to_value(ips_data, read_pos, 2)
                read_pos += 2

            if write_size > 0:
                # Normal patch. Verify array boundaries.
                if read_pos + write_size > len(ips_data):
                    raise Exception(
                        "IPS patch data has insufficient bytes for patch at read position "
                        + str(read_pos)
                        + " length "
                        + str(write_size)
                        + "."
                    )
            else:
                # RLE patch: fill a block of data with a single value.
                if read_pos + 2 > len(ips_data):
                    raise Exception(
                        "Insufficient bytes for patch size reading (2 bytes) at IPS patch read position "
                        + str(read_pos)
                        + "."
                    )
                elif read_pos + 3 > len(ips_data):
                    raise Exception(
                        "Insufficient bytes for RLE patch value reading (1 byte) at IPS patch read position "
                        + str(read_pos)
                        + "."
                    )
                else:
                    # Read 2 bytes in big endian - the RLE patch size.
                    rle_size = read_bytes_to_value(ips_data, read_pos, 2)
                    read_pos += 2

                    # Read 1 byte - the RLE patch value.
                    rle_value = ips_data[read_pos]
                    read_pos += 1

            if write_size > 0:
                # A normal patch.
                # Array boundaries have been checked before; this shouldn't throw.
                if write_pos + write_size > len(rom_data):
                    rom_data += (write_pos + write_size - len(rom_data)) * b"\x00"
                for i in range(write_size):
                    array_rom_data = bytearray(rom_data)
                    array_rom_data[write_pos + i] = ips_data[read_pos + i]
                    rom_data = bytes(array_rom_data)

                read_pos += write_size
            else:
                # RLE-encoded patch.
                if write_pos + rle_size > len(rom_data):
                    rom_data += (write_pos + rle_size - len(rom_data)) * b"\x00"
                for i in range(write_pos, write_pos + rle_size):
                    array_rom_data = bytearray(rom_data)
                    array_rom_data[i] = rle_value
                    rom_data = bytes(array_rom_data)

    else:
        raise Exception("IPS patch has invalid header.")

    if read_pos + 3 <= len(ips_data):
        # Truncate extension, for compatibility with Lunar IPS.
        truncate_length = 0
        truncate_length = read_bytes_to_value(ips_data, read_pos, 3)
        if truncate_length > len(rom_data):
            rom_data += (truncate_length - len(rom_data)) * b"\x00"

    return rom_data


def read_bytes_to_value(
    read_data: bytes,
    read_pos: int,
    read_size: int,
    read_endianness: Literal["little", "big"] = "big",
):
    dest = int.from_bytes(
        read_data[read_pos : read_pos + read_size],
        byteorder=read_endianness,
        signed=False,
    )
    return dest


def patch_complement_check(rom_data: bytes) -> bytes:
    if len(rom_data) > 0xBD:
        sum = 0
        for i in range(160, 189):
            sum -= rom_data[i]
        sum -= 0x19
        array_rom_data = bytearray(rom_data)
        array_rom_data[0xBD] = sum % 256  # Now it's unsigned char.

        return bytes(array_rom_data)
    else:
        raise Exception("Invalid ROM data; data size too small.")


def ips_patcher(
    rom_path: str, ips_path: str, out_path: str
) -> int:  # 0: Done 1: Failed
    print("Reading ROM file: " + rom_path)
    try:
        rom_data = open(rom_path, "rb").read()
    except:
        print("Error reading ROM file.")
        return 1
    print("Reading IPS patch: " + ips_path)
    try:
        ips_data = open(ips_path, "rb").read()
    except:
        print("Error reading IPS patch file.")
        return 1

    print("Applying IPS patch.")
    try:
        out_data = apply_ips_patch(rom_data, ips_data)
    except:
        print("Failed to apply IPS patch.")
        return 1

    print("Correcting complement checksum.")
    try:
        out_data = patch_complement_check(out_data)
    except:
        print("Error during complement check patch.")
        return 1

    print("Writing output file: " + out_path)
    try:
        with open(out_path, "wb") as out_file:
            out_file.write(out_data)
    except:
        print("Failed to write file.")
        return 1
    return 0
