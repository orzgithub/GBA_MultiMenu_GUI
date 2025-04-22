use std::{
    error::Error,
    fs::File,
    io::{Read, Write},
    mem,
    str,
};

use crate::payload_bin::PAYLOAD_BIN;

const ROM_SIZE: usize = 0x02000000;
const SIGNATURE: &[u8] = b"<3 from Maniac";

#[repr(usize)]
enum PayloadOffsets {
    OriginalEntrypointAddr = 0,
    FlushMode = 1,
    SaveSize = 2,
    PatchedEntrypoint = 3,
    WriteSramPatched = 4,
    WriteEepromPatched = 5,
    WriteFlashPatched = 6,
    WriteEepromV111Posthook = 7,
}

// ldr r3, [pc, # 0]; bx r3
static THUMB_BRANCH_THUNK: [u8; 4] = [0x00, 0x4b, 0x18, 0x47];
static ARM_BRANCH_THUNK: [u8; 8] = [0x00, 0x30, 0x9f, 0xe5, 0x13, 0xff, 0x2f, 0xe1];

static WRITE_SRAM_SIGNATURE: [u8; 16] = [
    0x30, 0xB5, 0x05, 0x1C, 0x0C, 0x1C, 0x13, 0x1C, 0x0B, 0x4A, 0x10, 0x88, 0x0B, 0x49, 0x08, 0x40,
];
static WRITE_SRAM2_SIGNATURE: [u8; 16] = [
    0x80, 0xb5, 0x83, 0xb0, 0x6f, 0x46, 0x38, 0x60, 0x79, 0x60, 0xba, 0x60, 0x09, 0x48, 0x09, 0x49,
];
static WRITE_SRAM_RAM_SIGNATURE: [u8; 16] = [
    0x04, 0xC0, 0x90, 0xE4, 0x01, 0xC0, 0xC1, 0xE4, 0x2C, 0xC4, 0xA0, 0xE1, 0x01, 0xC0, 0xC1, 0xE4,
];
static WRITE_EEPROM_SIGNATURE: [u8; 20] = [
    0x70, 0xB5, 0x00, 0x04, 0x0A, 0x1C, 0x40, 0x0B, 0xE0, 0x21, 0x09, 0x05, 0x41, 0x18, 0x07, 0x31,
    0x00, 0x23, 0x10, 0x78,
];
static WRITE_FLASH_SIGNATURE: [u8; 16] = [
    0x70, 0xB5, 0x00, 0x03, 0x0A, 0x1C, 0xE0, 0x21, 0x09, 0x05, 0x41, 0x18, 0x01, 0x23, 0x1B, 0x03,
];
static WRITE_FLASH2_SIGNATURE: [u8; 16] = [
    0x7C, 0xB5, 0x90, 0xB0, 0x00, 0x03, 0x0A, 0x1C, 0xE0, 0x21, 0x09, 0x05, 0x09, 0x18, 0x01, 0x23,
];
static WRITE_FLASH3_SIGNATURE: [u8; 16] = [
    0xF0, 0xB5, 0x90, 0xB0, 0x0F, 0x1C, 0x00, 0x04, 0x04, 0x0C, 0x03, 0x48, 0x00, 0x68, 0x40, 0x89,
];
static WRITE_EEPROMV11_EPILOGUE_PATCH: [u8; 4] = [0x07, 0x49, 0x08, 0x47];
static WRITE_EEPROMV111_SIGNATURE: [u8; 16] = [
    0x0A, 0x88, 0x80, 0x21, 0x09, 0x06, 0x0A, 0x43, 0x02, 0x60, 0x07, 0x48, 0x00, 0x47, 0x00, 0x00,
];

fn memfind(haystack: &[u8], needle: &[u8], stride: usize) -> Option<usize> {
    haystack
        .windows(needle.len())
        .step_by(stride)
        .position(|window| window == needle)
        .map(|pos| pos)
}

pub fn patch_rom(rom_path: &str, out_path: &str) -> Result<(), Box<dyn Error>> {
    let mut rom = vec![0xFF; ROM_SIZE];

    // Open and read ROM file
    let mut romfile = File::open(rom_path)?;
    let romsize = romfile.metadata()?.len() as usize;

    // Read exact number of bytes to avoid buffer fill error
    let mut buffer = vec![0u8; romsize];
    romfile.read_exact(&mut buffer)?;
    rom[..romsize].copy_from_slice(&buffer);

    if romsize > ROM_SIZE {
        return Err("ROM too large - not a GBA ROM?".into());
    }

    let mut romsize = romsize;
    if romsize & 0x3ffff != 0 {
        println!("ROM has been trimmed and is misaligned. Padding to 256KB alignment");
        romsize &= !0x3ffff;
        romsize += 0x40000;
    }

    // Check if ROM already patched.
    if memfind(&rom[..romsize], SIGNATURE, 4).is_some() {
        return Err("Signature found. ROM already patched!".into());
    }

    // Patch all references to IRQ handler address variable
    let old_irq_addr = [0xfc, 0x7f, 0x00, 0x03];
    let new_irq_addr = [0xf4, 0x7f, 0x00, 0x03];

    let mut found_irq = 0;
    for i in (0..romsize - 3).step_by(4) {
    if rom[i..i + 4] == old_irq_addr {
        found_irq += 1;
        println!("Found a reference to the IRQ handler address at {:x}, patching", i);
        rom[i..i + 4].copy_from_slice(&new_irq_addr);
    }
}

    if found_irq == 0 {
        return Err("Could not find any reference to the IRQ handler. Has the ROM already been patched?".into());
    }

    // Find a location to insert the payload immediately before a 0x40000 byte sector
    let payload_len = PAYLOAD_BIN.len();
    let mut payload_base = romsize as isize - 0x40000 - payload_len as isize;

    let mut found_space = false;
    while payload_base >= 0 {
        let start = payload_base as usize;
        let end = start + 0x40000 + payload_len;

        let is_all_zeroes = rom[start..end].iter().all(|&x| x == 0);
        let is_all_ones = rom[start..end].iter().all(|&x| x == 0xFF);

        if is_all_zeroes || is_all_ones {
            found_space = true;
            break;
        }

        payload_base -= 0x40000;
    }

    if !found_space {
        println!("ROM too small to install payload.");
        if romsize + 0x80000 > ROM_SIZE {
            return Err("ROM already max size. Cannot expand. Cannot install payload".into());
        } else {
            println!("Expanding ROM");
            romsize += 0x80000;
            payload_base = romsize as isize - 0x40000 - payload_len as isize;
            rom.resize(romsize, 0xFF);
        }
    }

    let payload_base = payload_base as usize;
    println!(
        "Installing payload at offset {:x}, save file stored at {:x}",
        payload_base,
        payload_base + payload_len
    );

    rom[payload_base..payload_base + payload_len].copy_from_slice(&PAYLOAD_BIN);

    let mode: u32 = 0;
    let flush_mode_offset = payload_base + mem::size_of::<u32>() * PayloadOffsets::FlushMode as usize;
    rom[flush_mode_offset..flush_mode_offset + 4].copy_from_slice(&mode.to_le_bytes());

    // Patch the ROM entrypoint
    if rom[3] != 0xea {
        return Err("Unexpected entrypoint instruction".into());
    }

    // Calculate original entrypoint following GBA header specification
    let original_entrypoint_offset =
        (rom[0] as u32) |
        ((rom[1] as u32) << 8) |
        ((rom[2] as u32) << 16);

    // Mask out thumb bit if present (bit0)
    let original_entrypoint_address =
        0x08000000 + 8 + (original_entrypoint_offset << 2) as usize;

    println!(
        "Original offset was {:08x}, original entrypoint was {:08x}",
        original_entrypoint_offset,
        original_entrypoint_address
    );

    // Store original entrypoint in payload header
    let original_entrypoint_offset = payload_base +
        std::mem::size_of::<u32>() * PayloadOffsets::OriginalEntrypointAddr as usize;
    rom[original_entrypoint_offset..original_entrypoint_offset + 4]
        .copy_from_slice(&(original_entrypoint_address as u32).to_le_bytes());

    // Calculate new entrypoint address
    let patched_entrypoint_offset = payload_base +
        std::mem::size_of::<u32>() * PayloadOffsets::PatchedEntrypoint as usize;
    let patched_entrypoint_value = u32::from_le_bytes([
        rom[patched_entrypoint_offset],
        rom[patched_entrypoint_offset + 1],
        rom[patched_entrypoint_offset + 2],
        rom[patched_entrypoint_offset + 3],
    ]);

    let new_entrypoint_address = 0x08000000 + payload_base + patched_entrypoint_value as usize;
    let new_entrypoint_offset = ((new_entrypoint_address - 0x08000008) >> 2) as u32;

    // Patch ROM header with new entrypoint
    rom[0..4].copy_from_slice(&(0xea000000 | new_entrypoint_offset).to_le_bytes());

    // Patch any write functions
    let mut found_write_location = false;
    let mut write_location = 0;
    while write_location < romsize - 64 {
        let save_size_offset = payload_base + mem::size_of::<u32>() * PayloadOffsets::SaveSize as usize;

        // Patch WriteSram function (Thumb mode)
        if rom[write_location..].starts_with(&WRITE_SRAM_SIGNATURE) {
            found_write_location = true;
            if mode == 0 {
                println!("WriteSram identified at offset {:x}, patching", write_location);
                // 1. Write Thumb branch thunk (ldr r3, [pc, #0]; bx r3)
                rom[write_location..write_location + THUMB_BRANCH_THUNK.len()]
                    .copy_from_slice(&THUMB_BRANCH_THUNK);

                // 2. Calculate target address from payload_bin
                let patch_offset = mem::size_of::<u32>() * PayloadOffsets::WriteSramPatched as usize;
                let target_offset = u32::from_le_bytes([
                    PAYLOAD_BIN[patch_offset],
                    PAYLOAD_BIN[patch_offset + 1],
                    PAYLOAD_BIN[patch_offset + 2],
                    PAYLOAD_BIN[patch_offset + 3],
                ]);

                // 3. Write target address (little-endian)
                let target_address = 0x08000000u32 + payload_base as u32 + target_offset;
                rom[write_location + 4..write_location + 8]
                    .copy_from_slice(&target_address.to_le_bytes());
            }
            rom[save_size_offset..save_size_offset + 4].copy_from_slice(&0x8000u32.to_le_bytes());
            write_location += WRITE_SRAM_SIGNATURE.len();
        }
        // Patch WriteSram2 function (Thumb mode variant)
        else if rom[write_location..].starts_with(&WRITE_SRAM2_SIGNATURE) {
            found_write_location = true;
            if mode == 0 {
                println!("WriteSram 2 identified at offset {:x}, patching", write_location);
                rom[write_location..write_location + THUMB_BRANCH_THUNK.len()]
                    .copy_from_slice(&THUMB_BRANCH_THUNK);

                let patch_offset = mem::size_of::<u32>() * PayloadOffsets::WriteSramPatched as usize;
                let target_offset = u32::from_le_bytes([
                    PAYLOAD_BIN[patch_offset],
                    PAYLOAD_BIN[patch_offset + 1],
                    PAYLOAD_BIN[patch_offset + 2],
                    PAYLOAD_BIN[patch_offset + 3],
                ]);

                let target_address = 0x08000000u32 + payload_base as u32 + target_offset;
                rom[write_location + 4..write_location + 8]
                    .copy_from_slice(&target_address.to_le_bytes());
            }
            rom[save_size_offset..save_size_offset + 4].copy_from_slice(&0x8000u32.to_le_bytes());
            write_location += WRITE_SRAM2_SIGNATURE.len();
        }
        // Patch WriteSramFast function (ARM mode)
        else if rom[write_location..].starts_with(&WRITE_SRAM_RAM_SIGNATURE) {
            found_write_location = true;
            if mode == 0 {
                println!("WriteSramFast identified at offset {:x}, patching", write_location);
                // 1. Write ARM branch thunk (ldr r0, [pc, #0x1c]; ldr r1, [pc, #0x1c]; bx r1)
                rom[write_location..write_location + ARM_BRANCH_THUNK.len()]
                    .copy_from_slice(&ARM_BRANCH_THUNK);

                // 2. Calculate target address from payload_bin
                let patch_offset = mem::size_of::<u32>() * PayloadOffsets::WriteSramPatched as usize;
                let target_offset = u32::from_le_bytes([
                    PAYLOAD_BIN[patch_offset],
                    PAYLOAD_BIN[patch_offset + 1],
                    PAYLOAD_BIN[patch_offset + 2],
                    PAYLOAD_BIN[patch_offset + 3],
                ]);

                // 3. Write target address (ARM mode uses 8-byte offset)
                let target_address = 0x08000000u32 + payload_base as u32 + target_offset;
                rom[write_location + 8..write_location + 12]
                    .copy_from_slice(&target_address.to_le_bytes());
            }
            rom[save_size_offset..save_size_offset + 4].copy_from_slice(&0x8000u32.to_le_bytes());
            write_location += WRITE_SRAM_RAM_SIGNATURE.len();
        }
        // Patch ProgramEepromDword (Thumb mode)
        else if rom[write_location..].starts_with(&WRITE_EEPROM_SIGNATURE) {
            found_write_location = true;
            if mode == 0 {
                println!("SRAM-patched ProgramEepromDword identified at offset {:x}, patching", write_location);
                rom[write_location..write_location + THUMB_BRANCH_THUNK.len()]
                    .copy_from_slice(&THUMB_BRANCH_THUNK);

                let patch_offset = mem::size_of::<u32>() * PayloadOffsets::WriteEepromPatched as usize;
                let target_offset = u32::from_le_bytes([
                    PAYLOAD_BIN[patch_offset],
                    PAYLOAD_BIN[patch_offset + 1],
                    PAYLOAD_BIN[patch_offset + 2],
                    PAYLOAD_BIN[patch_offset + 3],
                ]);

                let target_address = 0x08000000u32 + payload_base as u32 + target_offset;
                rom[write_location + 4..write_location + 8]
                    .copy_from_slice(&target_address.to_le_bytes());
            }
            rom[save_size_offset..save_size_offset + 4].copy_from_slice(&0x2000u32.to_le_bytes());
            write_location += WRITE_EEPROM_SIGNATURE.len();
        }
        // Patch Flash write functions (multiple variants)
        else if rom[write_location..].starts_with(&WRITE_FLASH_SIGNATURE) {
            found_write_location = true;
            if mode == 0 {
                println!("SRAM-patched flash write function 1 identified at offset {:x}", write_location);
                rom[write_location..write_location + THUMB_BRANCH_THUNK.len()]
                    .copy_from_slice(&THUMB_BRANCH_THUNK);

                let patch_offset = mem::size_of::<u32>() * PayloadOffsets::WriteFlashPatched as usize;
                let target_offset = u32::from_le_bytes([
                    PAYLOAD_BIN[patch_offset],
                    PAYLOAD_BIN[patch_offset + 1],
                    PAYLOAD_BIN[patch_offset + 2],
                    PAYLOAD_BIN[patch_offset + 3],
                ]);

                let target_address = 0x08000000u32 + payload_base as u32 + target_offset;
                rom[write_location + 4..write_location + 8]
                    .copy_from_slice(&target_address.to_le_bytes());
            }
            rom[save_size_offset..save_size_offset + 4].copy_from_slice(&0x10000u32.to_le_bytes());
            write_location += WRITE_FLASH_SIGNATURE.len();
        }
        else if rom[write_location..].starts_with(&WRITE_FLASH2_SIGNATURE) {
            found_write_location = true;
            if mode == 0 {
                println!("SRAM-patched flash write function2 identified at offset {:x}", write_location);
                rom[write_location..write_location + THUMB_BRANCH_THUNK.len()]
                    .copy_from_slice(&THUMB_BRANCH_THUNK);

                let patch_offset = mem::size_of::<u32>() * PayloadOffsets::WriteFlashPatched as usize;
                let target_offset = u32::from_le_bytes([
                    PAYLOAD_BIN[patch_offset],
                    PAYLOAD_BIN[patch_offset + 1],
                    PAYLOAD_BIN[patch_offset + 2],
                    PAYLOAD_BIN[patch_offset + 3],
                ]);

                let target_address = 0x08000000u32 + payload_base as u32 + target_offset;
                rom[write_location + 4..write_location + 8]
                    .copy_from_slice(&target_address.to_le_bytes());
            }
            rom[save_size_offset..save_size_offset + 4].copy_from_slice(&0x10000u32.to_le_bytes());
            write_location += WRITE_FLASH2_SIGNATURE.len();
        }
        else if rom[write_location..].starts_with(&WRITE_FLASH3_SIGNATURE) {
            found_write_location = true;
            if mode == 0 {
                println!("Flash write function 3 identified at offset {:x}", write_location);
                rom[write_location..write_location + THUMB_BRANCH_THUNK.len()]
                    .copy_from_slice(&THUMB_BRANCH_THUNK);

                let patch_offset = mem::size_of::<u32>() * PayloadOffsets::WriteFlashPatched as usize;
                let target_offset = u32::from_le_bytes([
                    PAYLOAD_BIN[patch_offset],
                    PAYLOAD_BIN[patch_offset + 1],
                    PAYLOAD_BIN[patch_offset + 2],
                    PAYLOAD_BIN[patch_offset + 3],
                ]);

                let target_address = 0x08000000u32 + payload_base as u32 + target_offset;
                rom[write_location + 4..write_location + 8]
                    .copy_from_slice(&target_address.to_le_bytes());
            }
            rom[save_size_offset..save_size_offset + 4].copy_from_slice(&0x20000u32.to_le_bytes());
            write_location += WRITE_FLASH3_SIGNATURE.len();
        }
        // Patch EEPROM_V111 epilogue
        else if rom[write_location..].starts_with(&WRITE_EEPROMV111_SIGNATURE) {
            found_write_location = true;
            if mode == 0 {
                println!("SRAM-patched EEPROM_V111 epilogue identified at offset {:x}", write_location);
                // Special 4-byte patch at offset +12
                rom[write_location + 12..write_location + 12 + WRITE_EEPROMV11_EPILOGUE_PATCH.len()]
                    .copy_from_slice(&WRITE_EEPROMV11_EPILOGUE_PATCH);

                // Write target address at offset +44
                let patch_offset = mem::size_of::<u32>() * PayloadOffsets::WriteEepromV111Posthook as usize;
                let target_offset = u32::from_le_bytes([
                    PAYLOAD_BIN[patch_offset],
                    PAYLOAD_BIN[patch_offset + 1],
                    PAYLOAD_BIN[patch_offset + 2],
                    PAYLOAD_BIN[patch_offset + 3],
                ]);

                let target_address = 0x08000000u32 + payload_base as u32 + target_offset;
                rom[write_location + 44..write_location + 48]
                    .copy_from_slice(&target_address.to_le_bytes());
            }
            rom[save_size_offset..save_size_offset + 4].copy_from_slice(&0x2000u32.to_le_bytes());
            write_location += WRITE_EEPROMV111_SIGNATURE.len();
        }
        else {
            // No signature match, advance 2 bytes (Thumb instruction alignment)
            write_location += 2;
        }
    }

    if !found_write_location {
        if mode == 0 {
            return Err("Could not find a write function to hook. Are you sure the game has save functionality and has been SRAM patched with GBATA?".into());
        } else {
            println!("Unsure what save type this is. Defaulting to 128KB save");
        }
    }

    // Write output file
    let mut outfile = File::create(out_path)?;
    outfile.write_all(&rom[..romsize])?;
    outfile.flush()?;

    println!("Patched successfully. Changes written to {}", out_path);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_memfind() {
        let data = b"abcdefghijklmnop";
        assert_eq!(memfind(data, b"def", 1), Some(3));
        assert_eq!(memfind(data, b"xyz", 1), None);
    }
}