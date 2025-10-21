#!/usr/bin/env python3
"""
Ported from original project. Rewrite original C code into Python.
The following license were from the original project.

License / 许可声明

未经授权，禁止用于商业行为。使用该代码的衍生项目需要保持开源，并且需要指明该项目的原始仓库地址（https://github.com/ArcheyChen/GBA-RTS-PATCH）。
代码中的 "Ausar'S-RTSFILE." 和 "<3 from Maniac" 等识别用字符串不应修改，而应当原样保留。

Commercial use is prohibited without authorization. Any derivative project using this code must remain open source and clearly indicate the original repository address (https://github.com/ArcheyChen/GBA-RTS-PATCH).
Identification strings in the code such as "Ausar'S-RTSFILE." and "<3 from Maniac" must not be altered and should be preserved as is.

免责声明 / Disclaimer
本代码按“原样”提供，不对其适用性、功能性或适合任何特定用途作出任何明示或暗示的保证。使用本代码所产生的任何后果和风险由使用者自行承担，作者不承担任何责任。
This code is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the code or the use or other dealings in the code.
"""

import os
import sys
import struct
import argparse
from typing import Optional, Tuple

from utils.PressAnyKey import press_any_key
from .payload_bin import payload_bin
payload_bin_len = len(payload_bin)

SIGNATURE = b"<3 from Maniac"
RTS_SIZE = 448 * 1024  # 448KB
MAX_ROM_SIZE = 0x02000000  # 32MB

WRITE_SRAM_SIGNATURE = bytes([0x30, 0xB5, 0x05, 0x1C, 0x0C, 0x1C, 0x13, 0x1C, 0x0B, 0x4A, 0x10, 0x88, 0x0B, 0x49, 0x08, 0x40])
WRITE_SRAM2_SIGNATURE = bytes([0x80, 0xb5, 0x83, 0xb0, 0x6f, 0x46, 0x38, 0x60, 0x79, 0x60, 0xba, 0x60, 0x09, 0x48, 0x09, 0x49])
WRITE_SRAM_RAM_SIGNATURE = bytes([0x04, 0xC0, 0x90, 0xE4, 0x01, 0xC0, 0xC1, 0xE4, 0x2C, 0xC4, 0xA0, 0xE1, 0x01, 0xC0, 0xC1, 0xE4])
WRITE_EEPROM_SIGNATURE = bytes([0x70, 0xB5, 0x00, 0x04, 0x0A, 0x1C, 0x40, 0x0B, 0xE0, 0x21, 0x09, 0x05, 0x41, 0x18, 0x07, 0x31, 0x00, 0x23, 0x10, 0x78])
WRITE_FLASH_SIGNATURE = bytes([0x70, 0xB5, 0x00, 0x03, 0x0A, 0x1C, 0xE0, 0x21, 0x09, 0x05, 0x41, 0x18, 0x01, 0x23, 0x1B, 0x03])
WRITE_FLASH2_SIGNATURE = bytes([0x7C, 0xB5, 0x90, 0xB0, 0x00, 0x03, 0x0A, 0x1C, 0xE0, 0x21, 0x09, 0x05, 0x09, 0x18, 0x01, 0x23])
WRITE_FLASH3_SIGNATURE = bytes([0xF0, 0xB5, 0x90, 0xB0, 0x0F, 0x1C, 0x00, 0x04, 0x04, 0x0C, 0x03, 0x48, 0x00, 0x68, 0x40, 0x89])
WRITE_EEPROMV111_SIGNATURE = bytes([0x0A, 0x88, 0x80, 0x21, 0x09, 0x06, 0x0A, 0x43, 0x02, 0x60, 0x07, 0x48, 0x00, 0x47, 0x00, 0x00])

OLD_IRQ_ADDR = bytes([0xfc, 0x7f, 0x00, 0x03])
NEW_IRQ_ADDR = bytes([0xf4, 0x7f, 0x00, 0x03])

class PayloadHeader:
    STRUCT_FORMAT = '<IIIIII'

    def __init__(self, data: bytes = None):
        if data and len(data) >= 24:
            values = struct.unpack(self.STRUCT_FORMAT, data[:24])
            self.original_entrypoint = values[0]
            self.ctrl_flag = values[1]
            self.rts_size = values[2]
            self.save_size = values[3]
            self.wbuf_size = values[4]
            self.patched_entrypoint_addr = values[5]
        else:
            self.original_entrypoint = 0
            self.ctrl_flag = 0
            self.rts_size = 0
            self.save_size = 0
            self.wbuf_size = 0
            self.patched_entrypoint_addr = 0

    def to_bytes(self) -> bytes:
        return struct.pack(self.STRUCT_FORMAT,
                           self.original_entrypoint,
                           self.ctrl_flag,
                           self.rts_size,
                           self.save_size,
                           self.wbuf_size,
                           self.patched_entrypoint_addr)

    def update_in_payload(self, payload_data: bytes) -> bytes:
        header_bytes = self.to_bytes()
        return header_bytes + payload_data[24:]

def memfind(haystack: bytes, needle: bytes, stride: int = 1) -> int:
    needle_len = len(needle)
    haystack_len = len(haystack)

    for i in range(0, haystack_len - needle_len + 1, stride):
        if haystack[i:i+needle_len] == needle:
            return i
    return -1

def detect_save_type(rom_data: bytes) -> Tuple[int, str]:
    signatures = [
        (WRITE_SRAM_SIGNATURE, 0x8000, "SRAM (32KB)"),
        (WRITE_SRAM2_SIGNATURE, 0x8000, "SRAM (32KB)"),
        (WRITE_SRAM_RAM_SIGNATURE, 0x8000, "SRAM (32KB)"),
        (WRITE_EEPROM_SIGNATURE, 0x2000, "EEPROM (8KB)"),
        (WRITE_EEPROMV111_SIGNATURE, 0x2000, "EEPROM (8KB)"),
        (WRITE_FLASH_SIGNATURE, 0x10000, "Flash (64KB)"),
        (WRITE_FLASH2_SIGNATURE, 0x10000, "Flash (64KB)"),
        (WRITE_FLASH3_SIGNATURE, 0x20000, "Flash (128KB)")
    ]

    for signature, save_size, save_type in signatures:
        pos = memfind(rom_data, signature, 2)
        if pos != -1:
            print(f"{save_type} save function detected at offset 0x{pos:08X} - Save size: {save_size // 1024}KB")
            return save_size, save_type

    print("No save function signatures found. Using default size: 128KB")
    return 0x20000, "Default (128KB)"

def patch_irq_references(rom_data: bytearray) -> int:
    found_count = 0
    data_len = len(rom_data)

    for i in range(0, data_len - 4, 4):
        if rom_data[i:i+4] == OLD_IRQ_ADDR:
            found_count += 1
            print(f"Found a reference to the IRQ handler address at 0x{i:08X}, patching")
            rom_data[i:i+4] = NEW_IRQ_ADDR

    return found_count

def find_payload_location(rom_data: bytes, reserved_space: int, sector_size: int) -> int:
    rom_size = len(rom_data)
    required_space = reserved_space + payload_bin_len

    for payload_base in range(rom_size - required_space - sector_size, -1, -sector_size):
        region = rom_data[payload_base:payload_base + required_space]
        if all(b == 0 for b in region) or all(b == 0xFF for b in region):
            return payload_base

    return -1

def parse_arm_branch_instruction(instruction_bytes: bytes) -> int:
    if len(instruction_bytes) != 4:
        return 0

    instruction = struct.unpack('<I', instruction_bytes)[0]
    if (instruction & 0xFF000000) != 0xEA000000:
        return 0

    offset = instruction & 0x00FFFFFF
    if offset & 0x00800000:
        offset |= 0xFF000000

    target_address = 0x08000000 + 8 + (offset * 4)
    return target_address

def create_arm_branch_instruction(target_address: int) -> bytes:
    offset = (target_address - 0x08000000 - 8) >> 2

    if offset > 0x00FFFFFF or offset < -0x00800000:
        raise ValueError("Branch target address out of range")

    offset &= 0x00FFFFFF

    instruction = 0xEA000000 | offset
    return struct.pack('<I', instruction)

def get_user_inputs(wbuf_size: Optional[int] = None, sector_size: Optional[int] = None) -> Tuple[int, int]:
    if wbuf_size is None:
        try:
            wbuf_input = input("Input write buffer size (0-4095, 0 for default): ")
            wbuf_size = int(wbuf_input)
            if wbuf_size < 0 or wbuf_size > 0xFFF:
                print("Invalid write buffer size, defaulting to 0")
                wbuf_size = 0
        except (ValueError, KeyboardInterrupt):
            print("Invalid input, defaulting to 0")
            wbuf_size = 0

    if sector_size is None:
        try:
            sector_input = input("Input sector size (0x10000-0x40000, 0x10000 for default): ")
            sector_size = int(sector_input, 0)
            if sector_size < 0x10000 or sector_size > 0x40000:
                print("Invalid sector size, defaulting to 0x10000")
                sector_size = 0x10000
        except (ValueError, KeyboardInterrupt):
            print("Invalid input, defaulting to 0x10000")
            sector_size = 0x10000

    return wbuf_size, sector_size

def apply_patch(rom_file: str, rts_file: Optional[str] = None,
                wbuf_size: Optional[int] = None, sector_size: Optional[int] = None,
                output_file: Optional[str] = None,
                interactive: bool = True) -> Tuple[bool, str]:
    """
    Apply RTS patch into GBA ROM

    Args:
        rom_file: input GBA ROM path
        rts_file: optional RTS file path
        wbuf_size: write buffer size (0-4095)
        sector_size: sector size (0x10000-0x40000)
        output_file: output GBA ROM path
        interactive: interactive mode

    Returns:
        Tuple[bool, str]: success or not and other info
    """

    if not os.path.exists(rom_file):
        return False, f"Input ROM file not found: {rom_file}"

    if rts_file and not os.path.exists(rts_file):
        return False, f"RTS file not found: {rts_file}"

    if interactive and (wbuf_size is None or sector_size is None):
        wbuf_size, sector_size = get_user_inputs(wbuf_size, sector_size)

    if wbuf_size is None:
        wbuf_size = 0
    if sector_size is None:
        sector_size = 0x10000

    if wbuf_size < 0 or wbuf_size > 0xFFF:
        return False, f"Invalid write buffer size: {wbuf_size} (must be 0-4095)"

    if sector_size < 0x10000 or sector_size > 0x40000:
        return False, f"Invalid sector size: 0x{sector_size:X} (must be 0x10000-0x40000)"

    try:
        if interactive:
            print(f"Reading ROM file: {rom_file}")
        with open(rom_file, 'rb') as f:
            rom_data = bytearray(f.read())

        rom_size = len(rom_data)
        if interactive:
            print(f"ROM size: {rom_size} bytes (0x{rom_size:X})")

        if rom_size > MAX_ROM_SIZE:
            return False, f"ROM too large (max 0x{MAX_ROM_SIZE:X} bytes)"

        if memfind(rom_data, SIGNATURE, 4) != -1:
            return False, "Signature found. ROM already patched!"

        if rom_size & 0x3FFFF:
            if interactive:
                print("ROM has been trimmed and is misaligned. Padding to 256KB alignment")
            rom_size = (rom_size & ~0x3FFFF) + 0x40000
            rom_data.extend(b'\xFF' * (rom_size - len(rom_data)))

        if interactive:
            print("Finding and patching IRQ handler address references...")
        found_irq = patch_irq_references(rom_data)
        if found_irq == 0:
            return False, "Could not find any reference to the IRQ handler. Has the ROM already been patched?"
        if interactive:
            print(f"Found and patched {found_irq} IRQ references")

        if interactive:
            print("Scanning ROM for save function signatures...")
        detected_save_size, save_type = detect_save_type(rom_data)

        if interactive:
            print("Final save configuration:")
            print(f"\tSave size: {detected_save_size // 1024} KB (0x{detected_save_size:X} bytes)")
            print(f"\tWrite buffer: {wbuf_size} bytes")
            print(f"\tSector size: 0x{sector_size:X} bytes")

        reserved_space = 0x70000  # 448KB
        reserved_space += detected_save_size
        if reserved_space % sector_size:
            reserved_space = reserved_space - (reserved_space % sector_size) + sector_size
            if interactive:
                print(f"Padding reserved space to 0x{reserved_space:X}")

        payload_base = find_payload_location(bytes(rom_data), reserved_space, 0x40000)

        if payload_base == -1:
            if interactive:
                print("ROM too small to install payload.")
            if rom_size + reserved_space > MAX_ROM_SIZE:
                return False, "ROM already max size. Cannot expand. Cannot install payload"
            else:
                if interactive:
                    print("Expanding ROM")
                new_size = rom_size + reserved_space
                rom_data.extend(b'\xFF' * (new_size - len(rom_data)))
                rom_size = new_size
                payload_base = rom_size - reserved_space - payload_bin_len

        if interactive:
            print(f"Installing payload at offset 0x{payload_base:X}")
            print(f"Payload ROM address: 0x{0x08000000 + payload_base:08X}")
            print(f"Payload size: {payload_bin_len} bytes (0x{payload_bin_len:X})")

        rom_data[payload_base:payload_base + payload_bin_len] = payload_bin

        header = PayloadHeader(rom_data[payload_base:payload_base + 24])
        header.rts_size = reserved_space
        header.save_size = detected_save_size
        header.wbuf_size = wbuf_size

        updated_header = header.to_bytes()
        rom_data[payload_base:payload_base + 24] = updated_header

        if interactive:
            print(f"  Combined rts_size field: 0x{header.rts_size:08X}")

        sram_save_base = payload_base + payload_bin_len
        if interactive:
            print(f"SRAM save space offset: 0x{sram_save_base:X}")
            print(f"SRAM save space ROM address: 0x{0x08000000 + sram_save_base:08X}")
            print(f"Reserved space size: {reserved_space // 1024} KB (0x{reserved_space:X} bytes)")

        if rts_file:
            if interactive:
                print(f"Embedding RTS file: {rts_file}")
            try:
                with open(rts_file, 'rb') as f:
                    rts_data = f.read()

                if len(rts_data) != RTS_SIZE:
                    return False, f"RTS file size must be exactly 448KB (458752 bytes), but got {len(rts_data)} bytes"

                rom_data[sram_save_base:sram_save_base + RTS_SIZE] = rts_data
                if interactive:
                    print(f"RTS file embedded successfully at offset 0x{sram_save_base:X}")
                    print("RTS covers sectors 0-6 (448KB) after payload")
            except Exception as e:
                return False, f"Failed to read RTS file: {e}"

        if rom_data[3] != 0xEA:
            return False, "Unexpected entrypoint instruction"

        original_entrypoint_address = parse_arm_branch_instruction(rom_data[0:4])
        if interactive:
            print(f"Original entrypoint address: 0x{original_entrypoint_address:08X}")

        header.original_entrypoint = original_entrypoint_address
        updated_header = header.to_bytes()
        rom_data[payload_base:payload_base + 24] = updated_header

        payload_header_in_bin = PayloadHeader(payload_bin[:24])
        new_entrypoint_address = 0x08000000 + payload_base + payload_header_in_bin.patched_entrypoint_addr

        new_branch_instruction = create_arm_branch_instruction(new_entrypoint_address)
        rom_data[0:4] = new_branch_instruction

        if output_file is None:
            base_name = os.path.splitext(rom_file)[0]
            output_file = f"{base_name}_rts_keypad_wb{wbuf_size}.gba"

        if interactive:
            print(f"Writing patched ROM: {output_file}")
        with open(output_file, 'wb') as f:
            f.write(rom_data[:rom_size])

        if interactive:
            print("Patched successfully!")
            print("RTS save: L + R + Start")
            print("RTS load: L + R + Select")

        return True, output_file

    except Exception as e:
        return False, f"Error during processing: {e}"

def print_license():
    # From the original code.
    print("=" * 60)
    print("License / 许可声明")
    print("未经授权，禁止用于商业行为。使用该代码的衍生项目需要保持开源，并且需要指明该项目的原始仓库地址（https://github.com/ArcheyChen/GBA-RTS-PATCH）。")
    print("代码中的 'Ausar'S-RTSFILE.' 和 '<3 from Maniac' 等识别用字符串不应修改，而应当原样保留。")
    print("")
    print("Commercial use is prohibited without authorization. Any derivative project using this code must remain open source and clearly indicate the original repository address (https://github.com/ArcheyChen/GBA-RTS-PATCH).")
    print("Identification strings in the code such as 'Ausar'S-RTSFILE.' and '<3 from Maniac' must not be altered and should be preserved as is.")
    print("")
    print("免责声明 / Disclaimer")
    print("本代码按\"原样\"提供，不对其适用性、功能性或适合任何特定用途作出任何明示或暗示的保证。使用本代码所产生的任何后果和风险由使用者自行承担，作者不承担任何责任。")
    print("This code is provided 'as is', without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the code or the use or other dealings in the code.")
    print("=" * 60)

def main():
    print_license()
    print("GBA RTS Patcher - Python version (Written by Ausar, Based on Maniac's batteryless patcher)")

    parser = argparse.ArgumentParser(description='GBA RTS Patcher')
    parser.add_argument('rom_file', help='GBA ROM file to patch')
    parser.add_argument('rts_file', nargs='?', help='Optional 448KB RTS save file to embed')
    parser.add_argument('--wbuf', type=int, default=None, help='Write buffer size (0-4095, default: 0)')
    parser.add_argument('--sector-size', type=lambda x: int(x, 0), default=None,
                        help='Sector size (0x10000-0x40000, default: 0x10000)')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--no-prompt', action='store_true', help='Skip user prompts')

    args = parser.parse_args()

    if not args.rom_file.lower().endswith('.gba'):
        print("Error: Input file must have .gba extension")
        if not args.no_prompt:
            press_any_key()
        return 1

    if args.rts_file and not args.rts_file.lower().endswith('.rts'):
        print("Error: RTS file must have .rts extension")
        if not args.no_prompt:
            press_any_key()
        return 1

    success, result = apply_patch(
        rom_file=args.rom_file,
        rts_file=args.rts_file,
        wbuf_size=args.wbuf,
        sector_size=args.sector_size,
        output_file=args.output,
        interactive=not args.no_prompt
    )

    if success:
        print(f"Successfully patched ROM. Changes written to {result}")
        if not args.no_prompt:
            press_any_key()
        return 0
    else:
        print(f"Error: {result}")
        if not args.no_prompt:
            press_any_key()
        return 1

if __name__ == "__main__":
    sys.exit(main())