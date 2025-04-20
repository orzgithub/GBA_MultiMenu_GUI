#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <pybind11/pybind11.h>

#include "payload_bin.hpp"

#ifdef _MSC_VER
#define strcasecmp _stricmp
#endif

namespace py = pybind11;

FILE *romfile;
FILE *outfile;
uint32_t romsize;
uint8_t rom[0x02000000];
unsigned char signature[] = "<3 from Maniac";

enum payload_offsets {
    ORIGINAL_ENTRYPOINT_ADDR,
    FLUSH_MODE,
    SAVE_SIZE,
    PATCHED_ENTRYPOINT,
    WRITE_SRAM_PATCHED,
    WRITE_EEPROM_PATCHED,
    WRITE_FLASH_PATCHED,
    WRITE_EEPROM_V111_POSTHOOK
};

// ldr r3, [pc, # 0]; bx r3
static unsigned char thumb_branch_thunk[] = { 0x00, 0x4b, 0x18, 0x47 };
static unsigned char arm_branch_thunk[] = { 0x00, 0x30, 0x9f, 0xe5, 0x13, 0xff, 0x2f, 0xe1 };

static unsigned char write_sram_signature[] = { 0x30, 0xB5, 0x05, 0x1C, 0x0C, 0x1C, 0x13, 0x1C, 0x0B, 0x4A, 0x10, 0x88, 0x0B, 0x49, 0x08, 0x40};
static unsigned char write_sram2_signature[] = { 0x80, 0xb5, 0x83, 0xb0, 0x6f, 0x46, 0x38, 0x60, 0x79, 0x60, 0xba, 0x60, 0x09, 0x48, 0x09, 0x49 };
static unsigned char write_sram_ram_signature[] = { 0x04, 0xC0, 0x90, 0xE4, 0x01, 0xC0, 0xC1, 0xE4, 0x2C, 0xC4, 0xA0, 0xE1, 0x01, 0xC0, 0xC1, 0xE4 };
static unsigned char write_eeprom_signature[] = { 0x70, 0xB5, 0x00, 0x04, 0x0A, 0x1C, 0x40, 0x0B, 0xE0, 0x21, 0x09, 0x05, 0x41, 0x18, 0x07, 0x31, 0x00, 0x23, 0x10, 0x78};
static unsigned char write_flash_signature[] = { 0x70, 0xB5, 0x00, 0x03, 0x0A, 0x1C, 0xE0, 0x21, 0x09, 0x05, 0x41, 0x18, 0x01, 0x23, 0x1B, 0x03};
static unsigned char write_flash2_signature[] = { 0x7C, 0xB5, 0x90, 0xB0, 0x00, 0x03, 0x0A, 0x1C, 0xE0, 0x21, 0x09, 0x05, 0x09, 0x18, 0x01, 0x23};
// sig present without SRAM patch
static unsigned char write_flash3_signature[] = { 0xF0, 0xB5, 0x90, 0xB0, 0x0F, 0x1C, 0x00, 0x04, 0x04, 0x0C, 0x03, 0x48, 0x00, 0x68, 0x40, 0x89 };

// This one is a pure nightmare. You are welcome to try doing this better, since it will probably trigger overeagerly...
// ldr r0, [pc, #0x1c]; ldr r1, [pc, #0x1c], bx r1
static unsigned char write_eepromv11_epilogue_patch[] = { 0x07, 0x49, 0x08, 0x47 };
static unsigned char write_eepromv111_signature[] = { 0x0A, 0x88, 0x80, 0x21, 0x09, 0x06, 0x0A, 0x43, 0x02, 0x60, 0x07, 0x48, 0x00, 0x47, 0x00, 0x00 };

static uint8_t *memfind(uint8_t *haystack, size_t haystack_size, uint8_t *needle, size_t needle_size, int stride)
{
    for (size_t i = 0; i < haystack_size - needle_size; i += stride)
    {
        if (!memcmp(haystack + i, needle, needle_size))
        {
            return haystack + i;
        }
    }
    return NULL;
}

int patch(char *rom_path, char *out_path)
{
	memset(rom, 0x00ff, sizeof rom);
    
    size_t romfilename_len = strlen(rom_path);
    if (romfilename_len < 4 || strcasecmp(rom_path + romfilename_len - 4, ".gba"))
    {
        puts("File does not have .gba extension.");
        return 1;
    }

    // Open ROM file
    if (!(romfile = fopen(rom_path, "rb")))
    {
        puts("Could not open input file");
        puts(strerror(errno));
        return 1;
    }

    // Load ROM into memory
    fseek(romfile, 0, SEEK_END);
    romsize = ftell(romfile);

    if (romsize > sizeof rom)
    {
        puts("ROM too large - not a GBA ROM?");
        return 1;
    }

    if (romsize & 0x3ffff)
    {
		puts("ROM has been trimmed and is misaligned. Padding to 256KB alignment");
		romsize &= ~0x3ffff;
		romsize += 0x40000;
    }

    fseek(romfile, 0, SEEK_SET);
    fread(rom, 1, romsize, romfile);

    // Check if ROM already patched.
    if (memfind(rom, romsize, signature, sizeof signature - 1, 4))
    {
        puts("Signature found. ROM already patched!");
        return 1;
    }

    // Patch all references to IRQ handler address variable
    uint8_t old_irq_addr[4] = { 0xfc, 0x7f, 0x00, 0x03 };
    uint8_t new_irq_addr[4] = { 0xf4, 0x7f, 0x00, 0x03 };

    int found_irq = 0;
    for (uint8_t *p = rom; p < rom + romsize; p += 4)
    {
        if (!memcmp(p, old_irq_addr, sizeof old_irq_addr))
        {
            ++found_irq;
			printf("Found a reference to the IRQ handler address at %lx, patching\n", p - rom);
            memcpy(p, new_irq_addr, sizeof new_irq_addr);
        }
    }
    if (!found_irq)
    {
        puts("Could not find any reference to the IRQ handler. Has the ROM already been patched?");
        return 1;
    }

    // Find a location to insert the payload immediately before a 0x40000 byte sector
	int payload_base;
    for (payload_base = romsize - 0x40000 - payload_bin_len; payload_base >= 0; payload_base -= 0x40000)
    {
        int is_all_zeroes = 1;
        int is_all_ones = 1;
        for (int i = 0; i < 0x40000 + payload_bin_len; ++i)
        {
            if (rom[payload_base+i] != 0)
            {
                is_all_zeroes = 0;
            }
            if (rom[payload_base+i] != 0xFF)
            {
                is_all_ones = 0;
            }
        }
        if (is_all_zeroes || is_all_ones)
        {
           break;
		}
    }
	if (payload_base < 0)
	{
		puts("ROM too small to install payload.");
		if (romsize + 0x80000 > 0x2000000)
		{
			puts("ROM alraedy max size. Cannot expand. Cannot install payload");
			return 0;
		}
		else
		{
			puts("Expanding ROM");
			romsize += 0x80000;
			payload_base = romsize - 0x40000 - payload_bin_len;
		}
	}
	
	printf("Installing payload at offset %x, save file stored at %x\n", payload_base, payload_base + payload_bin_len);
	memcpy(rom + payload_base, payload_bin, payload_bin_len);

    int mode = 0;
    *((uint32_t*)&rom[payload_base] + FLUSH_MODE) = mode;
    

	// Patch the ROM entrypoint to init sram and the dummy IRQ handler, and tell the new entrypoint where the old one was.
	if (rom[3] != 0xea)
	{
		puts("Unexpected entrypoint instruction");
		return 2;
	}
	unsigned long original_entrypoint_offset = rom[0];
	original_entrypoint_offset |= rom[1] << 8;
	original_entrypoint_offset |= rom[2] << 16;
	unsigned long original_entrypoint_address = 0x08000000 + 8 + (original_entrypoint_offset << 2);
	printf("Original offset was %lx, original entrypoint was %lx\n", original_entrypoint_offset, original_entrypoint_address);
	// little endian assumed, deal with it
    
    *((uint32_t*)&rom[payload_base] + ORIGINAL_ENTRYPOINT_ADDR) = original_entrypoint_address;

    unsigned long new_entrypoint_address = 0x08000000 + payload_base + *((uint32_t*)payload_bin + PATCHED_ENTRYPOINT);
	*(uint32_t*)rom = 0xea000000 | ((new_entrypoint_address - 0x08000008) >> 2);


	// Patch any write functions to install the countdown IRQ handler after calling any save function
    int found_write_location = 0;
    for (uint8_t *write_location = rom; write_location < rom + romsize - 64; write_location += 2)
    {
        int rom_offset = write_location - rom;
		if (!memcmp(write_location, write_sram_signature, sizeof write_sram_signature))
		{
            found_write_location = 1;
            if (!mode)
            {                
                printf("WriteSram identified at offset %lx, patching\n", write_location - rom);
                memcpy(write_location, thumb_branch_thunk, sizeof thumb_branch_thunk);
                *((uint32_t*)write_location + 1) = 0x08000000 + payload_base + *((uint32_t*)payload_bin + WRITE_SRAM_PATCHED);
            }
            *((uint32_t*)&rom[payload_base] + SAVE_SIZE) = 0x8000;

		}
        if (!memcmp(write_location, write_sram2_signature, sizeof write_sram2_signature))
		{
            found_write_location = 1;
            if (!mode)
            {                
                printf("WriteSram 2 identified at offset %lx, patching\n", write_location - rom);
                memcpy(write_location, thumb_branch_thunk, sizeof thumb_branch_thunk);
                *((uint32_t*)write_location + 1) = 0x08000000 + payload_base + *((uint32_t*)payload_bin + WRITE_SRAM_PATCHED);
            }
            *((uint32_t*)&rom[payload_base] + SAVE_SIZE) = 0x8000;

		}
		if (!memcmp(write_location, write_sram_ram_signature, sizeof write_sram_ram_signature))
		{
            found_write_location = 1;
            if (!mode)
            {
                printf("WriteSramFast identified at offset %lx, patching\n", write_location - rom);
                memcpy(write_location, arm_branch_thunk, sizeof arm_branch_thunk);
                *((uint32_t*)write_location + 2) = 0x08000000 + payload_base + *((uint32_t*)payload_bin + WRITE_SRAM_PATCHED);
            }
            *((uint32_t*)&rom[payload_base] + SAVE_SIZE) = 0x8000;
		}
		if (!memcmp(write_location, write_eeprom_signature, sizeof write_eeprom_signature))
		{
            found_write_location = 1;
            if (!mode)
            {
                printf("SRAM-patched ProgramEepromDword identified at offset %lx, patching\n", write_location - rom);
                memcpy(write_location, thumb_branch_thunk, sizeof thumb_branch_thunk);
                *((uint32_t*)write_location + 1) = 0x08000000 + payload_base + *((uint32_t*)payload_bin + WRITE_EEPROM_PATCHED);
            }
            // Unable to statically distinguish between EEPROM sizes - assume 64kbit to be safe.
            *((uint32_t*)&rom[payload_base] + SAVE_SIZE) = 0x2000;
		}
		if (!memcmp(write_location, write_flash_signature, sizeof write_flash_signature))
		{
            found_write_location = 1;
            if (!mode)
            {
                printf("SRAM-patched flash write function 1 identified at offset %lx\n", write_location - rom);
                memcpy(write_location, thumb_branch_thunk, sizeof thumb_branch_thunk);
                *((uint32_t*)write_location + 1) = 0x08000000 + payload_base + *((uint32_t*)payload_bin + WRITE_FLASH_PATCHED);
            }
            *((uint32_t*)&rom[payload_base] + SAVE_SIZE) = 0x10000;
		}
		if (!memcmp(write_location, write_flash2_signature, sizeof write_flash2_signature))
		{
            found_write_location = 1;
            if (!mode)
            {
                printf("SRAM-patched flash write function2  identified at offset %lx\n", write_location - rom);
                memcpy(write_location, thumb_branch_thunk, sizeof thumb_branch_thunk);
                *((uint32_t*)write_location + 1) = 0x08000000 + payload_base + *((uint32_t*)payload_bin + WRITE_FLASH_PATCHED);
            }
            *((uint32_t*)&rom[payload_base] + SAVE_SIZE) = 0x10000;
		}
		if (!memcmp(write_location, write_flash3_signature, sizeof write_flash3_signature))
		{
            found_write_location = 1;
            if (!mode)
            {
                printf("Flash write function 3 identified at offset %lx\n", write_location - rom);
                memcpy(write_location, thumb_branch_thunk, sizeof thumb_branch_thunk);
                *((uint32_t*)write_location + 1) = 0x08000000 + payload_base + *((uint32_t*)payload_bin + WRITE_FLASH_PATCHED);
            }
            // Assumed this signature only appears in FLASH1M
            *((uint32_t*)&rom[payload_base] + SAVE_SIZE) = 0x20000;
		}
        if (!memcmp(write_location, write_eepromv111_signature, sizeof write_eepromv111_signature))
        {
            found_write_location = 1;
            if (!mode)
            {
                printf("SRAM-patched EEPROM_V111 epilogue identified at offset %lx\n", write_location - rom);
                memcpy(write_location + 12, write_eepromv11_epilogue_patch, sizeof write_eepromv11_epilogue_patch);
                *((uint32_t*)write_location + 11) = 0x08000000 + payload_base + *((uint32_t*)payload_bin + WRITE_EEPROM_V111_POSTHOOK);
            }

            // Unable to statically distinguish between EEPROM sizes - assume 64kbit to be safe.
            *((uint32_t*)&rom[payload_base] + SAVE_SIZE) = 0x2000;
        }
	}
    if (!found_write_location)
    {
        if (!mode)
        {
            puts("Could not find a write function to hook. Are you sure the game has save functionality and has been SRAM patched with GBATA?");
            return 1;
        }
        else
        {
            puts("Unsure what save type this is. Defaulting to 128KB save");
        }
    }


	// Flush all changes to new file
    
    if (!(outfile = fopen(out_path, "wb")))
    {
        puts("Could not open output file");
        puts(strerror(errno));
        return 2;
    }
    
    fwrite(rom, 1, romsize, outfile);
    fflush(outfile);

    printf("Patched successfully. Changes written to %s\n",out_path);
    fclose(outfile);
	return 0;
	
}

PYBIND11_MODULE(batteryless_patch, m) {
    m.def("patch", &patch, py::arg("rom_path"), py::arg("out_path"));
}
