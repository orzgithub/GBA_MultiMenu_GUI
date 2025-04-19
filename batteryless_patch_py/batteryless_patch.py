import os
import struct
from .payload_bin import payload_bin

ORIGINAL_ENTRYPOINT_ADDR = 0
FLUSH_MODE = 1
SAVE_SIZE = 2
PATCHED_ENTRYPOINT = 3
WRITE_SRAM_PATCHED = 4
WRITE_EEPROM_PATCHED = 5
WRITE_FLASH_PATCHED = 6
WRITE_EEPROM_V111_POSTHOOK = 7

signature = b"<3 from Maniac"

thumb_branch_thunk = bytes([0x00, 0x4B, 0x18, 0x47])
arm_branch_thunk = bytes([0x00, 0x30, 0x9F, 0xE5, 0x13, 0xFF, 0x2F, 0xE1])

write_sram_signature = bytes(
    [
        0x30,
        0xB5,
        0x05,
        0x1C,
        0x0C,
        0x1C,
        0x13,
        0x1C,
        0x0B,
        0x4A,
        0x10,
        0x88,
        0x0B,
        0x49,
        0x08,
        0x40,
    ]
)
write_sram2_signature = bytes(
    [
        0x80,
        0xB5,
        0x83,
        0xB0,
        0x6F,
        0x46,
        0x38,
        0x60,
        0x79,
        0x60,
        0xBA,
        0x60,
        0x09,
        0x48,
        0x09,
        0x49,
    ]
)
write_sram_ram_signature = bytes(
    [
        0x04,
        0xC0,
        0x90,
        0xE4,
        0x01,
        0xC0,
        0xC1,
        0xE4,
        0x2C,
        0xC4,
        0xA0,
        0xE1,
        0x01,
        0xC0,
        0xC1,
        0xE4,
    ]
)
write_eeprom_signature = bytes(
    [
        0x70,
        0xB5,
        0x00,
        0x04,
        0x0A,
        0x1C,
        0x40,
        0x0B,
        0xE0,
        0x21,
        0x09,
        0x05,
        0x41,
        0x18,
        0x07,
        0x31,
        0x00,
        0x23,
        0x10,
        0x78,
    ]
)
write_flash_signature = bytes(
    [
        0x70,
        0xB5,
        0x00,
        0x03,
        0x0A,
        0x1C,
        0xE0,
        0x21,
        0x09,
        0x05,
        0x41,
        0x18,
        0x01,
        0x23,
        0x1B,
        0x03,
    ]
)
write_flash2_signature = bytes(
    [
        0x7C,
        0xB5,
        0x90,
        0xB0,
        0x00,
        0x03,
        0x0A,
        0x1C,
        0xE0,
        0x21,
        0x09,
        0x05,
        0x09,
        0x18,
        0x01,
        0x23,
    ]
)
write_flash3_signature = bytes(
    [
        0xF0,
        0xB5,
        0x90,
        0xB0,
        0x0F,
        0x1C,
        0x00,
        0x04,
        0x04,
        0x0C,
        0x03,
        0x48,
        0x00,
        0x68,
        0x40,
        0x89,
    ]
)
write_eepromv11_epilogue_patch = bytes([0x07, 0x49, 0x08, 0x47])
write_eepromv111_signature = bytes(
    [
        0x0A,
        0x88,
        0x80,
        0x21,
        0x09,
        0x06,
        0x0A,
        0x43,
        0x02,
        0x60,
        0x07,
        0x48,
        0x00,
        0x47,
        0x00,
        0x00,
    ]
)


def memfind(haystack, needle, stride=4):
    """find needle byte array in haystack"""
    needle_len = len(needle)
    for i in range(0, len(haystack) - needle_len + 1, stride):
        if haystack[i : i + needle_len] == needle:
            return i
    return None


def patch(rom_path, out_path):
    """Main patch function"""
    if not rom_path.lower().endswith(".gba"):
        print("File does not have .gba extension.")
        return 1

        # Read ROM file
    try:
        with open(rom_path, "rb") as f:
            rom = bytearray(f.read())
    except IOError as e:
        print(f"Could not open input file: {e}")
        return 1

    romsize = len(rom)
    max_rom_size = 0x02000000

    # Check ROM size
    if romsize > max_rom_size:
        print("ROM too large - not a GBA ROM?")
        return 1

    # Handle alignment
    if romsize & 0x3FFFF:
        print("ROM has been trimmed and is misaligned. Padding to 256KB alignment")
        romsize = (romsize & ~0x3FFFF) + 0x40000
        rom.extend(b"\xff" * (romsize - len(rom)))

    # Check if already patched
    if memfind(rom, signature) is not None:
        print("Signature found. ROM already patched!")
        return 1

    # Patch IRQ handler references
    old_irq_addr = bytes([0xFC, 0x7F, 0x00, 0x03])
    new_irq_addr = bytes([0xF4, 0x7F, 0x00, 0x03])

    found_irq = 0
    pos = 0
    while True:
        idx = memfind(rom[pos:], old_irq_addr)
        if idx is None:
            break
        idx += pos
        found_irq += 1
        print(f"Found a reference to the IRQ handler address at {hex(idx)}, patching")
        rom[idx : idx + 4] = new_irq_addr
        pos = idx + 4

    if not found_irq:
        print(
            "Could not find any reference to the IRQ handler. Has the ROM already been patched?"
        )
        return 1

    # Find payload location
    payload_base = None
    for base in range(romsize - 0x40000 - len(payload_bin), -1, -0x40000):
        region = rom[base : base + 0x40000 + len(payload_bin)]
        if all(b == 0 for b in region) or all(b == 0xFF for b in region):
            payload_base = base
            break

    if payload_base is None:
        print("ROM too small to install payload.")
        if romsize + 0x80000 > max_rom_size:
            print("ROM already max size. Cannot expand. Cannot install payload")
            return 1
        else:
            print("Expanding ROM")
            romsize += 0x80000
            rom.extend(b"\xff" * 0x80000)
            payload_base = romsize - 0x40000 - len(payload_bin)

    print(
        f"Installing payload at offset {hex(payload_base)}, save file stored at {hex(payload_base + len(payload_bin))}"
    )
    rom[payload_base : payload_base + len(payload_bin)] = payload_bin

    # Set flush mode
    mode = 0
    struct.pack_into("<I", rom, payload_base + FLUSH_MODE * 4, mode)

    # Patch ROM entrypoint
    if rom[3] != 0xEA:
        print("Unexpected entrypoint instruction")
        return 2

    original_entrypoint_offset = rom[0] | (rom[1] << 8) | (rom[2] << 16)
    original_entrypoint_address = 0x08000000 + 8 + (original_entrypoint_offset << 2)
    print(
        f"Original offset was {hex(original_entrypoint_offset)}, original entrypoint was {hex(original_entrypoint_address)}"
    )

    # Store original entrypoint address in payload
    struct.pack_into(
        "<I",
        rom,
        payload_base + ORIGINAL_ENTRYPOINT_ADDR * 4,
        original_entrypoint_address,
    )

    # Calculate new entrypoint address
    patched_entrypoint_offset = struct.unpack_from(
        "<I", payload_bin, PATCHED_ENTRYPOINT * 4
    )[0]
    new_entrypoint_address = 0x08000000 + payload_base + patched_entrypoint_offset

    # Modify ROM entrypoint
    new_offset = (new_entrypoint_address - 0x08000008) >> 2
    rom[0:4] = struct.pack("<I", 0xEA000000 | (new_offset & 0x00FFFFFF))

    # Find and patch write functions
    found_write_location = False
    save_size = None

    # Define signature handlers
    def patch_thumb(rom, offset, payload_base, payload_offset):
        rom[offset : offset + 4] = thumb_branch_thunk
        target_addr = (
            0x08000000
            + payload_base
            + struct.unpack_from("<I", payload_bin, payload_offset * 4)[0]
        )
        rom[offset + 4 : offset + 8] = struct.pack("<I", target_addr)

    def patch_arm(rom, offset, payload_base, payload_offset):
        rom[offset : offset + 8] = arm_branch_thunk
        target_addr = (
            0x08000000
            + payload_base
            + struct.unpack_from("<I", payload_bin, payload_offset * 4)[0]
        )
        rom[offset + 8 : offset + 12] = struct.pack("<I", target_addr)

    def patch_eeprom_v111(rom, offset, payload_base, payload_offset):
        rom[offset + 12 : offset + 16] = write_eepromv11_epilogue_patch
        target_addr = (
            0x08000000
            + payload_base
            + struct.unpack_from("<I", payload_bin, payload_offset * 4)[0]
        )
        rom[offset + 11 * 4 : offset + 12 * 4] = struct.pack("<I", target_addr)

    # Signature patterns and their handlers
    signatures = [
        (write_sram_signature, patch_thumb, WRITE_SRAM_PATCHED, 0x8000),
        (write_sram2_signature, patch_thumb, WRITE_SRAM_PATCHED, 0x8000),
        (write_sram_ram_signature, patch_arm, WRITE_SRAM_PATCHED, 0x8000),
        (write_eeprom_signature, patch_thumb, WRITE_EEPROM_PATCHED, 0x2000),
        (write_flash_signature, patch_thumb, WRITE_FLASH_PATCHED, 0x10000),
        (write_flash2_signature, patch_thumb, WRITE_FLASH_PATCHED, 0x10000),
        (write_flash3_signature, patch_thumb, WRITE_FLASH_PATCHED, 0x20000),
    ]

    # Process all signatures
    for sig, handler, offset, size in signatures:
        pos = 0
        while True:
            idx = memfind(rom[pos:], sig)
            if idx is None:
                break
            idx += pos
            found_write_location = True
            print(f"Found write function at offset {hex(idx)}, patching")

            if not mode:
                handler(rom, idx, payload_base, offset)

            save_size = size
            pos = idx + len(sig)

    # Special handling for EEPROM V111
    pos = 0
    while True:
        idx = memfind(rom[pos:], write_eepromv111_signature)
        if idx is None:
            break
        idx += pos
        found_write_location = True
        print(f"Found EEPROM V111 function at offset {hex(idx)}, patching")

        if not mode:
            patch_eeprom_v111(rom, idx, payload_base, WRITE_EEPROM_V111_POSTHOOK)

        save_size = 0x2000
        pos = idx + len(write_eepromv111_signature)

    if not found_write_location:
        if not mode:
            print(
                "Could not find a write function to hook. Are you sure the game has save functionality and has been SRAM patched with GBATA?"
            )
            return 1
        else:
            print("Unsure what save type this is. Defaulting to 128KB save")
            save_size = 0x20000

    if save_size is not None:
        struct.pack_into("<I", rom, payload_base + SAVE_SIZE * 4, save_size)

    # Write output file
    try:
        with open(out_path, "wb") as f:
            f.write(rom)
        print(f"Patched successfully. Changes written to {out_path}")
    except IOError as e:
        print(f"Could not open output file: {e}")
        return 2

    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: batteryless_patch.py input.gba output.gba")
        sys.exit(1)
    sys.exit(patch(sys.argv[1], sys.argv[2]))
