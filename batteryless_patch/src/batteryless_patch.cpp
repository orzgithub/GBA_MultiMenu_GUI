#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <fstream>
#include <memory>
#include <algorithm>
#include <iostream>

#include <pybind11/pybind11.h>

#include "payload_bin.hpp"

#ifdef _MSC_VER
#define strcasecmp _stricmp
#endif

namespace py = pybind11;

class ROMPatcher {
private:
    std::vector<uint8_t> rom_data;
    uint32_t rom_size;

    static constexpr size_t MAX_ROM_SIZE = 0x02000000;
    static constexpr std::array<uint8_t, 14> SIGNATURE = {'<','3',' ','f','r','o','m',' ','M','a','n','i','a','c'};

    enum PayloadOffsets {
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
    static constexpr std::array<uint8_t, 4> THUMB_BRANCH_THUNK = {0x00, 0x4b, 0x18, 0x47};
    static constexpr std::array<uint8_t, 8> ARM_BRANCH_THUNK = {0x00, 0x30, 0x9f, 0xe5, 0x13, 0xff, 0x2f, 0xe1};

    static constexpr std::array<uint8_t, 16> WRITE_SRAM_SIGNATURE = {0x30, 0xB5, 0x05, 0x1C, 0x0C, 0x1C, 0x13, 0x1C, 0x0B, 0x4A, 0x10, 0x88, 0x0B, 0x49, 0x08, 0x40};
    static constexpr std::array<uint8_t, 16> WRITE_SRAM2_SIGNATURE = {0x80, 0xb5, 0x83, 0xb0, 0x6f, 0x46, 0x38, 0x60, 0x79, 0x60, 0xba, 0x60, 0x09, 0x48, 0x09, 0x49};
    static constexpr std::array<uint8_t, 16> WRITE_SRAM_RAM_SIGNATURE = {0x04, 0xC0, 0x90, 0xE4, 0x01, 0xC0, 0xC1, 0xE4, 0x2C, 0xC4, 0xA0, 0xE1, 0x01, 0xC0, 0xC1, 0xE4};
    static constexpr std::array<uint8_t, 20> WRITE_EEPROM_SIGNATURE = {0x70, 0xB5, 0x00, 0x04, 0x0A, 0x1C, 0x40, 0x0B, 0xE0, 0x21, 0x09, 0x05, 0x41, 0x18, 0x07, 0x31, 0x00, 0x23, 0x10, 0x78};
    static constexpr std::array<uint8_t, 16> WRITE_FLASH_SIGNATURE = {0x70, 0xB5, 0x00, 0x03, 0x0A, 0x1C, 0xE0, 0x21, 0x09, 0x05, 0x41, 0x18, 0x01, 0x23, 0x1B, 0x03};
    static constexpr std::array<uint8_t, 16> WRITE_FLASH2_SIGNATURE = {0x7C, 0xB5, 0x90, 0xB0, 0x00, 0x03, 0x0A, 0x1C, 0xE0, 0x21, 0x09, 0x05, 0x09, 0x18, 0x01, 0x23};
    // sig present without SRAM patch
    static constexpr std::array<uint8_t, 16> WRITE_FLASH3_SIGNATURE = {0xF0, 0xB5, 0x90, 0xB0, 0x0F, 0x1C, 0x00, 0x04, 0x04, 0x0C, 0x03, 0x48, 0x00, 0x68, 0x40, 0x89};

    // This one is a pure nightmare. You are welcome to try doing this better, since it will probably trigger overeagerly...
    // ldr r0, [pc, #0x1c]; ldr r1, [pc, #0x1c], bx r1
    static constexpr std::array<uint8_t, 4> WRITE_EEPROMV11_EPILOGUE_PATCH = {0x07, 0x49, 0x08, 0x47};
    static constexpr std::array<uint8_t, 16> WRITE_EEPROMV111_SIGNATURE = {0x0A, 0x88, 0x80, 0x21, 0x09, 0x06, 0x0A, 0x43, 0x02, 0x60, 0x07, 0x48, 0x00, 0x47, 0x00, 0x00};

    size_t find_pattern(const std::vector<uint8_t>& data, const std::vector<uint8_t>& pattern, size_t stride = 1) {
        for (size_t i = 0; i <= data.size() - pattern.size(); i += stride) {
            if (std::equal(pattern.begin(), pattern.end(), data.begin() + i)) {
                return i;
            }
        }
        return data.size();
    }

    bool load_rom(const std::string& rom_path) {
        std::ifstream file(rom_path, std::ios::binary | std::ios::ate);
        if (!file.is_open()) {
            std::cerr << "Could not open input file: " << std::strerror(errno) << std::endl;
            return false;
        }

        rom_size = static_cast<uint32_t>(file.tellg());
        if (rom_size > MAX_ROM_SIZE) {
            std::cerr << "ROM too large - not a GBA ROM?" << std::endl;
            return false;
        }

        if (rom_size & 0x3ffff) {
            std::cout << "ROM has been trimmed and is misaligned. Padding to 256KB alignment" << std::endl;
            rom_size &= ~0x3ffff;
            rom_size += 0x40000;
        }

        rom_data.resize(MAX_ROM_SIZE, 0xFF);
        file.seekg(0);
        file.read(reinterpret_cast<char*>(rom_data.data()), rom_size);

        return !file.fail();
    }

    bool save_rom(const std::string& out_path) {
        std::ofstream file(out_path, std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "Could not open output file: " << std::strerror(errno) << std::endl;
            return false;
        }

        file.write(reinterpret_cast<const char*>(rom_data.data()), rom_size);
        return !file.fail();
    }

    bool is_already_patched() {
        std::vector<uint8_t> sig_vec(SIGNATURE.begin(), SIGNATURE.end());
        return find_pattern(rom_data, sig_vec, 4) != rom_data.size();
    }

    bool patch_irq_handler() {
        const std::array<uint8_t, 4> OLD_IRQ_ADDR = {0xfc, 0x7f, 0x00, 0x03};
        const std::array<uint8_t, 4> NEW_IRQ_ADDR = {0xf4, 0x7f, 0x00, 0x03};

        int found_irq = 0;
        for (size_t i = 0; i < rom_size; i += 4) {
            if (std::equal(OLD_IRQ_ADDR.begin(), OLD_IRQ_ADDR.end(), rom_data.begin() + i)) {
                ++found_irq;
                std::cout << "Found a reference to the IRQ handler address at " << std::hex << i << ", patching" << std::endl;
                std::copy(NEW_IRQ_ADDR.begin(), NEW_IRQ_ADDR.end(), rom_data.begin() + i);
            }
        }

        if (!found_irq) {
            std::cerr << "Could not find any reference to the IRQ handler. Has the ROM already been patched?" << std::endl;
            return false;
        }
        return true;
    }

    int find_payload_base() {
        for (int payload_base = rom_size - 0x40000 - payload_bin_len; payload_base >= 0; payload_base -= 0x40000) {
            bool is_all_zeroes = true;
            bool is_all_ones = true;

            for (int i = 0; i < 0x40000 + payload_bin_len; ++i) {
                if (rom_data[payload_base + i] != 0) is_all_zeroes = false;
                if (rom_data[payload_base + i] != 0xFF) is_all_ones = false;
                if (!is_all_zeroes && !is_all_ones) break;
            }

            if (is_all_zeroes || is_all_ones) {
                return payload_base;
            }
        }
        return -1;
    }

    void patch_write_function(size_t offset, const std::vector<uint8_t>& patch_bytes, uint32_t branch_target, uint32_t save_size, int payload_base, const std::string& description) {
        std::copy(patch_bytes.begin(), patch_bytes.end(), rom_data.begin() + offset);
        *reinterpret_cast<uint32_t*>(&rom_data[offset + patch_bytes.size()]) = 0x08000000 + payload_base + branch_target;
        *reinterpret_cast<uint32_t*>(&rom_data[payload_base + SAVE_SIZE * 4]) = save_size;
        std::cout << description << " identified at offset " << std::hex << offset << ", patching" << std::endl;
    }

    bool patch_write_functions(int payload_base, int mode) {
        bool found_write_location = false;
        std::vector<uint8_t> thumb_thunk_vec(THUMB_BRANCH_THUNK.begin(), THUMB_BRANCH_THUNK.end());
        std::vector<uint8_t> arm_thunk_vec(ARM_BRANCH_THUNK.begin(), ARM_BRANCH_THUNK.end());
        std::vector<uint8_t> eeprom_patch_vec(WRITE_EEPROMV11_EPILOGUE_PATCH.begin(), WRITE_EEPROMV11_EPILOGUE_PATCH.end());

        auto check_and_patch = [&](const auto& signature, const auto& patch_bytes, uint32_t branch_target,
                                 uint32_t save_size, const std::string& description, bool is_arm = false) {
            std::vector<uint8_t> sig_vec(signature.begin(), signature.end());
            std::vector<uint8_t> patch_vec(patch_bytes.begin(), patch_bytes.end());

            for (size_t offset = 0; offset <= rom_size - sig_vec.size(); offset += 2) {
                if (std::equal(sig_vec.begin(), sig_vec.end(), rom_data.begin() + offset)) {
                    found_write_location = true;
                    if (!mode) {
                        if (is_arm) {
                            std::copy(patch_vec.begin(), patch_vec.end(), rom_data.begin() + offset);
                            *reinterpret_cast<uint32_t*>(&rom_data[offset + 8]) = 0x08000000 + payload_base + branch_target;
                        } else {
                            patch_write_function(offset, patch_vec, branch_target, save_size, payload_base, description);
                        }
                    }
                    *reinterpret_cast<uint32_t*>(&rom_data[payload_base + SAVE_SIZE * 4]) = save_size;
                    return true;
                }
            }
            return false;
        };

        check_and_patch(WRITE_SRAM_SIGNATURE, THUMB_BRANCH_THUNK,
                       *reinterpret_cast<const uint32_t*>(payload_bin + WRITE_SRAM_PATCHED * 4),
                       0x8000, "WriteSram");

        check_and_patch(WRITE_SRAM2_SIGNATURE, THUMB_BRANCH_THUNK,
                       *reinterpret_cast<const uint32_t*>(payload_bin + WRITE_SRAM_PATCHED * 4),
                       0x8000, "WriteSram 2");

        check_and_patch(WRITE_SRAM_RAM_SIGNATURE, ARM_BRANCH_THUNK,
                       *reinterpret_cast<const uint32_t*>(payload_bin + WRITE_SRAM_PATCHED * 4),
                       0x8000, "WriteSramFast", true);

        check_and_patch(WRITE_EEPROM_SIGNATURE, THUMB_BRANCH_THUNK,
                       *reinterpret_cast<const uint32_t*>(payload_bin + WRITE_EEPROM_PATCHED * 4),
                       0x2000, "SRAM-patched ProgramEepromDword");

        check_and_patch(WRITE_FLASH_SIGNATURE, THUMB_BRANCH_THUNK,
                       *reinterpret_cast<const uint32_t*>(payload_bin + WRITE_FLASH_PATCHED * 4),
                       0x10000, "SRAM-patched flash write function 1");

        check_and_patch(WRITE_FLASH2_SIGNATURE, THUMB_BRANCH_THUNK,
                       *reinterpret_cast<const uint32_t*>(payload_bin + WRITE_FLASH_PATCHED * 4),
                       0x10000, "SRAM-patched flash write function 2");

        check_and_patch(WRITE_FLASH3_SIGNATURE, THUMB_BRANCH_THUNK,
                       *reinterpret_cast<const uint32_t*>(payload_bin + WRITE_FLASH_PATCHED * 4),
                       0x20000, "Flash write function 3");

        std::vector<uint8_t> eeprom_sig_vec(WRITE_EEPROMV111_SIGNATURE.begin(), WRITE_EEPROMV111_SIGNATURE.end());
        for (size_t offset = 0; offset <= rom_size - eeprom_sig_vec.size(); offset += 2) {
            if (std::equal(eeprom_sig_vec.begin(), eeprom_sig_vec.end(), rom_data.begin() + offset)) {
                found_write_location = true;
                if (!mode) {
                    std::cout << "SRAM-patched EEPROM_V111 epilogue identified at offset " << std::hex << offset << std::endl;
                    std::copy(eeprom_patch_vec.begin(), eeprom_patch_vec.end(), rom_data.begin() + offset + 12);
                    *reinterpret_cast<uint32_t*>(&rom_data[offset + 44]) = 0x08000000 + payload_base +
                        *reinterpret_cast<const uint32_t*>(payload_bin + WRITE_EEPROM_V111_POSTHOOK * 4);
                }
                *reinterpret_cast<uint32_t*>(&rom_data[payload_base + SAVE_SIZE * 4]) = 0x2000;
                break;
            }
        }

        if (!found_write_location) {
            if (!mode) {
                std::cerr << "Could not find a write function to hook. Are you sure the game has save functionality and has been SRAM patched with GBATA?" << std::endl;
                return false;
            } else {
                std::cout << "Unsure what save type this is. Defaulting to 128KB save" << std::endl;
            }
        }
        return true;
    }

public:
    int patch(const std::string& rom_path, const std::string& out_path, bool auto_mode) {
        if (rom_path.length() < 4 || strcasecmp(rom_path.c_str() + rom_path.length() - 4, ".gba")) {
            std::cerr << "File does not have .gba extension." << std::endl;
            return 1;
        }

        if (!load_rom(rom_path)) {
            return 1;
        }

        if (is_already_patched()) {
            std::cerr << "Signature found. ROM already patched!" << std::endl;
            return 1;
        }

        if (!patch_irq_handler()) {
            return 1;
        }

        int payload_base = find_payload_base();
        if (payload_base < 0) {
            std::cout << "ROM too small to install payload." << std::endl;
            if (rom_size + 0x80000 > MAX_ROM_SIZE) {
                std::cerr << "ROM already max size. Cannot expand. Cannot install payload" << std::endl;
                return 1;
            } else {
                std::cout << "Expanding ROM" << std::endl;
                rom_size += 0x80000;
                payload_base = rom_size - 0x40000 - payload_bin_len;
            }
        }

        std::cout << "Installing payload at offset " << std::hex << payload_base
                  << ", save file stored at " << std::hex << (payload_base + payload_bin_len) << std::endl;

        std::copy(payload_bin, payload_bin + payload_bin_len, rom_data.begin() + payload_base);

        int mode = auto_mode ? 0 : 1;
        *reinterpret_cast<uint32_t*>(&rom_data[payload_base + FLUSH_MODE * 4]) = mode;

        if (rom_data[3] != 0xea) {
            std::cerr << "Unexpected entrypoint instruction" << std::endl;
            return 2;
        }

        uint32_t original_entrypoint_offset = rom_data[0] | (rom_data[1] << 8) | (rom_data[2] << 16);
        uint32_t original_entrypoint_address = 0x08000000 + 8 + (original_entrypoint_offset << 2);
        std::cout << "Original offset was " << std::hex << original_entrypoint_offset
                  << ", original entrypoint was " << std::hex << original_entrypoint_address << std::endl;

        *reinterpret_cast<uint32_t*>(&rom_data[payload_base + ORIGINAL_ENTRYPOINT_ADDR * 4]) = original_entrypoint_address;

        uint32_t new_entrypoint_address = 0x08000000 + payload_base +
            *reinterpret_cast<const uint32_t*>(payload_bin + PATCHED_ENTRYPOINT * 4);
        *reinterpret_cast<uint32_t*>(&rom_data[0]) = 0xea000000 | ((new_entrypoint_address - 0x08000008) >> 2);

        if (!patch_write_functions(payload_base, mode) && !mode) {
            return 1;
        }

        if (!save_rom(out_path)) {
            return 2;
        }

        std::cout << "Patched successfully. Changes written to " << out_path << std::endl;
        return 0;
    }
};

int patch(const char* rom_path, const char* out_path, bool auto_mode) {
    ROMPatcher patcher;
    return patcher.patch(rom_path, out_path, auto_mode);
}

PYBIND11_MODULE(batteryless_patch, m) {
    m.def("patch", &patch, py::arg("rom_path"), py::arg("out_path"), py::arg("auto_mode"));
}