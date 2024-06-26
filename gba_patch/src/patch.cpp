#include <cassert>
#include <cstddef>
#include <algorithm>
#include <limits>
#include <sstream>
#include <vector>

#include <boost/assign.hpp>
#include <boost/lexical_cast.hpp>

#include "error.hpp"
#include "patch.hpp"


#ifdef _WIN32
	typedef __int32 int32_t;
	typedef __int16 int16_t;
	typedef unsigned __int32 uint32_t;
	typedef unsigned __int16 uint16_t;
#else
	#include <stdint.h>
#endif


struct RomPatch {
	const std::vector<unsigned char> find_data;
	const std::vector<unsigned char> replacement_data;
	const std::vector<bool> find_mask;
	const std::vector<bool> replacement_mask;

	RomPatch(const std::vector<unsigned char> find_data,
			 const std::vector<unsigned char> replacement_data,
			 const std::vector<bool> find_mask = std::vector<bool>(),
			 const std::vector<bool> replacement_mask = std::vector<bool>())
			: find_data(find_data), replacement_data(replacement_data),
			  find_mask(find_mask), replacement_mask(replacement_mask) {}
};


void patch_complement_check(std::vector<unsigned char> & rom_data) {
	if (rom_data.size() > 0xbd) {
		// A byte is always 8 bits in D.
		unsigned char sum = 0;

		for (size_t i=160; i < 189; i++) {
			sum -= rom_data[i];
		}

		sum -= 0x19;

		rom_data[0xbd] = sum;
	} else {
		throw MalformedDataException("Invalid ROM data; data size too small.");
	}
}


void uniformize_rom_padding(std::vector<unsigned char> &rom_data, const size_t alignment) {
	// According to Merriam-Webster, "uniformize" is indeed a real word.
	// TODO Optimize/remove duplicate code.
	if (rom_data.size() > 0) {
		unsigned char empty = rom_data.back();

		size_t rom_eod = find_rom_eod(rom_data);
		size_t begin = alignment > 0 ? next_aligned_address(rom_eod, alignment) : rom_eod;

		if (begin < ((size_t) 0) - 1 && begin < rom_data.size()) {
			for (size_t i = begin; i < rom_data.size(); i++) {
				if (rom_data[i] != empty) {
					rom_data[i] = empty;
				}
			}
		}
	}
}


void trim_padding(std::vector<unsigned char> &rom_data, const size_t alignment, const bool interchangeable_empty_byte) {
	if (rom_data.size() > 0) {
		size_t rom_eod = find_rom_eod(rom_data, interchangeable_empty_byte);
		size_t cutoff = alignment > 0 ? next_aligned_address(rom_eod, alignment) - 1 : rom_eod;
		rom_data.resize(cutoff + 1);
	}
}


void apply_ips_patch(std::vector<unsigned char> &data, const std::vector<unsigned char> &ips_patch) {
	if (ips_patch.size() < 5) {
		throw MalformedDataException("Missing IPS header (5 bytes) at position 0x00.");
	} else {
		// TODO Clean up vector slice comparison.
		bool a = ips_patch[0] == 0x50;
		bool b = ips_patch[1] == 0x41;
		bool c = ips_patch[2] == 0x54;
		bool d = ips_patch[3] == 0x43;
		bool e = ips_patch[4] == 0x48;

		if (!a || !b || !c || !d || !e) {
			throw MalformedDataException("IPS patch has invalid header.");
		}
	}

	size_t read_pos = 5;

	while (read_pos < ips_patch.size()) {
		uint32_t write_pos = 0;
		uint32_t write_size = 0;
		uint32_t rle_size = 0;
		unsigned char rle_value = 0x00;

		// Read 3 bytes in big endian - the write position.
		if (read_pos + 3 > ips_patch.size()) {
			std::string error = "Insufficient bytes for offset reading (3 bytes) at IPS patch read position ";
			error += boost::lexical_cast<std::string>(read_pos);
			error += ".";
			throw MalformedDataException(error);
		} else {
			bool a = ips_patch[read_pos+0] == 0x45;
			bool b = ips_patch[read_pos+1] == 0x4F;
			bool c = ips_patch[read_pos+2] == 0x46;

			if (a && b && c) {
				read_pos += 3;
				break;
			} else {
				read_bytes_to_value(write_pos, ips_patch, read_pos, 3);
				read_pos += 3;
			}
		}

		// Read 2 bytes in big endian - the write length.
		if (read_pos + 2 > ips_patch.size()) {
			std::string error = "Insufficient bytes for patch size reading (2 bytes) at IPS patch read position ";
			error += boost::lexical_cast<std::string>(read_pos);
			throw MalformedDataException(error);
		} else {
			read_bytes_to_value(write_size, ips_patch, read_pos, 2);
			read_pos += 2;
		}

		if (write_size > 0) {
			// Normal patch. Verify array boundaries.
			if (read_pos + write_size > ips_patch.size()) {
				std::string error = "IPS patch data has insufficient bytes for patch at read position ";
				error += boost::lexical_cast<std::string>(read_pos);
				error += " length ";
				error += boost::lexical_cast<std::string>(write_size);
				error += ".";
				throw MalformedDataException(error);
			}
		} else {
			// RLE patch: fill a block of data with a single value.
			if (read_pos + 2 > ips_patch.size()) {
				std::string error = "Insufficient bytes for RLE patch size reading (2 bytes) at IPS patch read position ";
				error += boost::lexical_cast<std::string>(read_pos);
				error += ".";
				throw MalformedDataException(error);
			} else if (read_pos + 3 > ips_patch.size()) {
				std::string error = "Insufficient bytes for RLE patch value reading (1 byte) at IPS patch read position ";
				error += boost::lexical_cast<std::string>(read_pos);
				error += ".";
				throw MalformedDataException(error);
			} else {
				// Read 2 bytes in big endian - the RLE patch size.
				read_bytes_to_value(rle_size, ips_patch, read_pos, 2);
				read_pos += 2;

				// Read 1 byte - the RLE patch value.
				rle_value = ips_patch[read_pos];
				read_pos += 1;
			}
		}

		if (write_size > 0) {
			// A normal patch.
			// Array boundaries have been checked before; this shouldn't throw.
			data.resize(write_pos+write_size > data.size() ? write_pos+write_size : data.size());

			for (size_t i=0; i < write_size; i++) {
				data[write_pos+i] = ips_patch[read_pos+i];
			}

			read_pos += write_size;
		} else {
			// RLE-encoded patch.
			data.resize(write_pos+rle_size > data.size() ? write_pos+rle_size : data.size());

			for (size_t i=write_pos; i < write_pos+rle_size; i++) {
				data[i] = rle_value;
			}
		}
	}

	if (read_pos + 3 <= ips_patch.size()) {
		// Truncate extension, for compatibility with Lunar IPS.
		uint32_t truncate_length = 0;
		read_bytes_to_value(truncate_length, ips_patch, read_pos, 3);
		data.resize(truncate_length);
	}
}


const std::vector<RomPatch> SRAM_PATCHES_FLASH1M_V102 = boost::assign::list_of
	(RomPatch(
		boost::assign::list_of
			(0xaa)(0x21)(0x19)(0x70)(0x05)(0x4a)(0x55)(0x21)(0x11)(0x70)(0xb0)(0x21)(0x19)(0x70)(0xe0)(0x21)
			(0x09)(0x05)(0x08)(0x70)(0x70)(0x47)(0x55)(0x55)(0x00)(0x0e)(0xaa)(0x2a)(0x00)(0x0e)(0x30)(0xb5)
			(0x91)(0xb0)(0x68)(0x46)(0x00)(0xf0)(0xf3)(0xf8)(0x6d)(0x46)(0x01)(0x35)(0x06)(0x4a)(0xaa)(0x20)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of
			(0x80)(0x21)(0x09)(0x02)(0x09)(0x22)(0x12)(0x06)(0x9f)(0x44)(0x11)(0x80)(0x03)(0x49)(0xc3)(0x02)
			(0xc9)(0x18)(0x11)(0x80)(0x70)(0x47)(0xfe)(0xff)(0xff)(0x01)(0x00)(0x00)(0x00)(0x00)(0x30)(0xb5)
			(0x91)(0xb0)(0x68)(0x46)(0x00)(0xf0)(0xf3)(0xf8)(0x6d)(0x46)(0x01)(0x35)(0x06)(0x4a)(0xaa)(0x20)
			(0x00)(0x00)(0x05)(0x49)(0x55)(0x20)(0x00)(0x00)(0x90)(0x20)(0x00)(0x00)(0x10)(0xa9)(0x03)(0x4a)
			(0x10)(0x1c)(0x08)(0xe0)(0x00)(0x00)(0x55)(0x55)(0x00)(0x0e)(0xaa)(0x2a)(0x00)(0x0e)(0x20)(0x4e)
			(0x00)(0x00)(0x08)(0x88)(0x01)(0x38)(0x08)(0x80)(0x08)(0x88)(0x00)(0x28)(0xf9)(0xd1)(0x0c)(0x48)
			(0x13)(0x20)(0x13)(0x20)(0x00)(0x06)(0x04)(0x0c)(0xe0)(0x20)(0x00)(0x05)(0x62)(0x20)(0x62)(0x20)
			(0x00)(0x06)(0x00)(0x0e)(0x04)(0x43)(0x07)(0x49)(0xaa)(0x20)(0x00)(0x00)(0x07)(0x4a)(0x55)(0x20)
			(0x00)(0x00)(0xf0)(0x20)(0x00)(0x00)(0x00)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0x14)(0x49)(0xaa)(0x24)(0x0c)(0x70)(0x13)(0x4b)(0x55)(0x22)(0x1a)(0x70)(0x80)(0x20)(0x08)(0x70)
			(0x0c)(0x70)(0x1a)(0x70)(0x10)(0x20)(0x08)(0x70)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of
			(0x0e)(0x21)(0x09)(0x06)(0xff)(0x24)(0x80)(0x22)(0x13)(0x4b)(0x52)(0x02)(0x01)(0x3a)(0x8c)(0x54)
			(0xfc)(0xd1)(0x00)(0x00)(0x00)(0x00)(0x00)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0xaa)(0x25)(0x0d)(0x70)(0x13)(0x4b)(0x55)(0x22)(0x1a)(0x70)(0x80)(0x20)(0x08)(0x70)(0x0d)(0x70)
			(0x1a)(0x70)(0x30)(0x20)(0x20)(0x70)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of
			(0xff)(0x25)(0x08)(0x22)(0x00)(0x00)(0x52)(0x02)(0x01)(0x3a)(0xa5)(0x54)(0xfc)(0xd1)(0x00)(0x00)
			(0x00)(0x00)(0x00)(0x00)(0x00)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0x22)(0x70)(0x09)(0x4b)(0x55)(0x22)(0x1a)(0x70)(0xa0)(0x22)(0x22)(0x70)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of
			(0x00)(0x00)(0x09)(0x4b)(0x55)(0x22)(0x00)(0x00)(0xa0)(0x22)(0x00)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
	));


const std::vector<RomPatch> SRAM_PATCHES_FLASH1M_V103 = boost::assign::list_of
	(RomPatch(
		boost::assign::list_of
			(0x05)(0x4b)(0xaa)(0x21)(0x19)(0x70)(0x05)(0x4a)(0x55)(0x21)(0x11)(0x70)(0xb0)(0x21)(0x19)(0x70)
			(0xe0)(0x21)(0x09)(0x05)(0x08)(0x70)(0x70)(0x47)(0x55)(0x55)(0x00)(0x0e)(0xaa)(0x2a)(0x00)(0x0e)
			(0x30)(0xb5)(0x91)(0xb0)(0x68)(0x46)(0x00)(0xf0)(0xf3)(0xf8)(0x6d)(0x46)(0x01)(0x35)(0x06)(0x4a)
			(0xaa)(0x20)(0x10)(0x70)(0x05)(0x49)(0x55)(0x20)(0x08)(0x70)(0x90)(0x20)(0x10)(0x70)(0x10)(0xa9)
			(0x03)(0x4a)(0x10)(0x1c)(0x08)(0xe0)(0x00)(0x00)(0x55)(0x55)(0x00)(0x0e)(0xaa)(0x2a)(0x00)(0x0e)
			(0x20)(0x4e)(0x00)(0x00)(0x08)(0x88)(0x01)(0x38)(0x08)(0x80)(0x08)(0x88)(0x00)(0x28)(0xf9)(0xd1)
			(0x0c)(0x48)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x05)(0x4b)(0x80)(0x21)(0x09)(0x02)(0x09)(0x22)(0x12)(0x06)(0x9f)(0x44)(0x11)(0x80)(0x03)(0x49)
			(0xc3)(0x02)(0xc9)(0x18)(0x11)(0x80)(0x70)(0x47)(0xfe)(0xff)(0xff)(0x01)(0x00)(0x00)(0x00)(0x00)
			(0x30)(0xb5)(0x91)(0xb0)(0x68)(0x46)(0x00)(0xf0)(0xf3)(0xf8)(0x6d)(0x46)(0x01)(0x35)(0x06)(0x4a)
			(0xaa)(0x20)(0x00)(0x00)(0x05)(0x49)(0x55)(0x20)(0x00)(0x00)(0x90)(0x20)(0x00)(0x00)(0x10)(0xa9)
			(0x03)(0x4a)(0x10)(0x1c)(0x08)(0xe0)(0x00)(0x00)(0x55)(0x55)(0x00)(0x0e)(0xaa)(0x2a)(0x00)(0x0e)
			(0x20)(0x4e)(0x00)(0x00)(0x08)(0x88)(0x01)(0x38)(0x08)(0x80)(0x08)(0x88)(0x00)(0x28)(0xf9)(0xd1)
			(0x0c)(0x48)(0x13)(0x20)(0x13)(0x20)(0x00)(0x06)(0x04)(0x0c)(0xe0)(0x20)(0x00)(0x05)(0x62)(0x20)
			(0x62)(0x20)(0x00)(0x06)(0x00)(0x0e)(0x04)(0x43)(0x07)(0x49)(0xaa)(0x20)(0x00)(0x00)(0x07)(0x4a)
			(0x55)(0x20)(0x00)(0x00)(0xf0)(0x20)(0x00)(0x00)(0x00)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
		
	))
	(RomPatch(
		boost::assign::list_of
			(0x14)(0x49)(0xaa)(0x24)(0x0c)(0x70)(0x13)(0x4b)(0x55)(0x22)(0x1a)(0x70)(0x80)(0x20)(0x08)(0x70)
			(0x0c)(0x70)(0x1a)(0x70)(0x10)(0x20)(0x08)(0x70)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x0e)(0x21)(0x09)(0x06)(0xff)(0x24)(0x80)(0x22)(0x13)(0x4b)(0x52)(0x02)(0x01)(0x3a)(0x8c)(0x54)
			(0xfc)(0xd1)(0x00)(0x00)(0x00)(0x00)(0x00)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0xaa)(0x25)(0x0d)(0x70)(0x14)(0x4b)(0x55)(0x22)(0x1a)(0x70)(0x80)(0x20)(0x08)(0x70)(0x0d)(0x70)
			(0x1a)(0x70)(0x30)(0x20)(0x20)(0x70)
			.convert_to_container<std::vector<unsigned char>>(),
			
		boost::assign::list_of
			(0xff)(0x25)(0x08)(0x22)(0x00)(0x00)(0x52)(0x02)(0x01)(0x3a)(0xa5)(0x54)(0xfc)(0xd1)(0x00)(0x00)
			(0x00)(0x00)(0x00)(0x00)(0x00)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of(0x10)(0x70)(0x0b)(0x49)(0x55)(0x20)(0x08)(0x70)(0xa0)(0x20)(0x10)(0x70)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of(0x00)(0x00)(0x0b)(0x49)(0x55)(0x20)(0x00)(0x00)(0xa0)(0x20)(0x00)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of(0x22)(0x70)(0x09)(0x4b)(0x55)(0x22)(0x1a)(0x70)(0xa0)(0x22)(0x22)(0x70)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of(0x00)(0x00)(0x09)(0x4b)(0x55)(0x22)(0x00)(0x00)(0xa0)(0x22)(0x00)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
	));


// FLASH512_V130 and V131 have all the same patches.
// TODO Check if FLASH512_V133 patch works correctly. Patches are from gbatemp thread, but gbata doesn't actually support V133.
const std::vector<RomPatch> SRAM_PATCHES_FLASH512_V13X = boost::assign::list_of
	(RomPatch(
		boost::assign::list_of
			(0xf0)(0xb5)(0xa0)(0xb0)(0x0d)(0x1c)(0x16)(0x1c)(0x1f)(0x1c)(0x03)(0x04)(0x1c)(0x0c)(0x0f)(0x4a)
			(0x10)(0x88)(0x0f)(0x49)(0x08)(0x40)(0x03)(0x21)(0x08)(0x43)(0x10)(0x80)(0x0d)(0x48)(0x00)(0x68)
			(0x01)(0x68)(0x80)(0x20)(0x80)(0x02)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x70)(0xb5)(0xa0)(0xb0)(0x00)(0x03)(0x40)(0x18)(0xe0)(0x21)(0x09)(0x05)(0x09)(0x18)(0x08)(0x78)
			(0x10)(0x70)(0x01)(0x3b)(0x01)(0x32)(0x01)(0x31)(0x00)(0x2b)(0xf8)(0xd1)(0x00)(0x20)(0x20)(0xb0)
			(0x70)(0xbc)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of(0xff)(0xf7)(0x88)(0xfd)(0x00)(0x04)(0x03)(0x0c).convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of(0x1b)(0x23)(0x1b)(0x02)(0x32)(0x20)(0x03)(0x43).convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of(0x70)(0xb5)(0x90)(0xb0)(0x15)(0x4d)(0x29)(0x88).convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of(0x00)(0xb5)(0x00)(0x20)(0x02)(0xbc)(0x08)(0x47).convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of(0x70)(0xb5)(0x46)(0x46)(0x40)(0xb4)(0x90)(0xb0).convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of(0x00)(0xb5)(0x00)(0x20)(0x02)(0xbc)(0x08)(0x47).convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0xf0)(0xb5)(0x90)(0xb0)(0x0f)(0x1c)(0x00)(0x04)(0x04)(0x0c)(0x03)(0x48)(0x00)(0x68)(0x40)(0x89)
			(0x84)(0x42)(0x05)(0xd3)(0x01)(0x48)(0x41)(0xe0)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of
			(0x7c)(0xb5)(0x90)(0xb0)(0x00)(0x03)(0x0a)(0x1c)(0xe0)(0x21)(0x09)(0x05)(0x09)(0x18)(0x01)(0x23)
			(0x1b)(0x03)(0x10)(0x78)(0x08)(0x70)(0x01)(0x3b)(0x01)(0x32)(0x01)(0x31)(0x00)(0x2b)(0xf8)(0xd1)
			(0x00)(0x20)(0x10)(0xb0)(0x7c)(0xbc)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>()
	));


// Encompasses EEPROM_V120, V121, and V122.
const std::vector<RomPatch> SRAM_PATCHES_EEPROM_V12X = boost::assign::list_of
	(RomPatch(
		// Wildcard: V120: 0x48, V121: 0x48 (?), V122: 0x44
		boost::assign::list_of
			(0xa2)(0xb0)(0x0d)(0x1c)(0x00)(0x04)(0x03)(0x0c)(0x03)(0x48)(0x00)(0x68)(0x80)(0x88)(0x83)(0x42)
			(0x05)(0xd3)(0x01)(0x48)(   0)(0xe0)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x00)(0x04)(0x0a)(0x1c)(0x40)(0x0b)(0xe0)(0x21)(0x09)(0x05)(0x41)(0x18)(0x07)(0x31)(0x00)(0x23)
			(0x08)(0x78)(0x10)(0x70)(0x01)(0x33)(0x01)(0x32)(0x01)(0x39)(0x07)(0x2b)(0xf8)(0xd9)(0x00)(0x20)
			(0x70)(0xbc)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)
			(false)(false)(false)(false)(true)(false)
			.convert_to_container<std::vector<bool>>()
	))
	(RomPatch(
		// Wildcard: V120: 0x59, V121: 0x59 (?), V122: 0x55
		boost::assign::list_of
			(0x30)(0xb5)(0xa9)(0xb0)(0x0d)(0x1c)(0x00)(0x04)(0x04)(0x0c)(0x03)(0x48)(0x00)(0x68)(0x80)(0x88)
			(0x84)(0x42)(0x05)(0xd3)(0x01)(0x48)(   0)(0xe0)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x70)(0xb5)(0x00)(0x04)(0x0a)(0x1c)(0x40)(0x0b)(0xe0)(0x21)(0x09)(0x05)(0x41)(0x18)(0x07)(0x31)
			(0x00)(0x23)(0x10)(0x78)(0x08)(0x70)(0x01)(0x33)(0x01)(0x32)(0x01)(0x39)(0x07)(0x2b)(0xf8)(0xd9)
			(0x00)(0x20)(0x70)(0xbc)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)
			(false)(false)(false)(false)(false)(false)( true)(false) // GBATemp guide's 0 was 0x59
			.convert_to_container<std::vector<bool>>()
	));


const std::vector<RomPatch> SRAM_PATCHES_EEPROM_V124 = boost::assign::list_of
	// TODO Test if wildcard is necessary for EEPROM_V124.
	// TODO Moeroe!! Jaleco Collection (J) can't be SRAM patched. gbata can't patch this game either.

	// GBATemp guide had 0x48 instead of wildcard, which was incorrect for a lot of ROMs.
	// gbata had 0x44 in that position instead. Unsure if all EEPROM_V124 ROMs require 0x44, or if GBATemp guide was just wrong.
	
	(RomPatch(
		boost::assign::list_of
			(0xa2)(0xb0)(0x0d)(0x1c)(0x00)(0x04)(0x03)(0x0c)(0x03)(0x48)(0x00)(0x68)(0x80)(0x88)(0x83)(0x42)
			(0x05)(0xd3)(0x01)(0x48)(   0)(0xe0)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x00)(0x04)(0x0a)(0x1c)(0x40)(0x0b)(0xe0)(0x21)(0x09)(0x05)(0x41)(0x18)(0x07)(0x31)(0x00)(0x23)
			(0x08)(0x78)(0x10)(0x70)(0x01)(0x33)(0x01)(0x32)(0x01)(0x39)(0x07)(0x2b)(0xf8)(0xd9)(0x00)(0x20)
			(0x70)(0xbc)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)(false)
			(false)(false)(false)(false)( true)(false)
			.convert_to_container<std::vector<bool>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0xf0)(0xb5)(0xac)(0xb0)(0x0d)(0x1c)(0x00)(0x04)(0x01)(0x0c)(0x12)(0x06)(0x17)(0x0e)(0x03)(0x48)
			(0x00)(0x68)(0x80)(0x88)(0x81)(0x42)(0x05)(0xd3)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x70)(0xb5)(0x00)(0x04)(0x0a)(0x1c)(0x40)(0x0b)(0xe0)(0x21)(0x09)(0x05)(0x41)(0x18)(0x07)(0x31)
			(0x00)(0x23)(0x10)(0x78)(0x08)(0x70)(0x01)(0x33)(0x01)(0x32)(0x01)(0x39)(0x07)(0x2b)(0xf8)(0xd9)
			(0x00)(0x20)(0x70)(0xbc)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>()
	));


const std::vector<RomPatch> SRAM_PATCHES_EEPROM_V126 = boost::assign::list_of
	(RomPatch(
		// Search pattern 1 differs from the guide on GBATemp by a single byte.
		boost::assign::list_of
			(0xa2)(0xb0)(0x0d)(0x1c)(0x00)(0x04)(0x03)(0x0c)(0x03)(0x48)(0x00)(0x68)(0x80)(0x88)(0x83)(0x42)
			(0x05)(0xd3)(0x01)(0x48)(0x4a)(0xe0)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x00)(0x04)(0x0a)(0x1c)(0x40)(0x0b)(0xe0)(0x21)(0x09)(0x05)(0x41)(0x18)(0x07)(0x31)(0x00)(0x23)
			(0x08)(0x78)(0x10)(0x70)(0x01)(0x33)(0x01)(0x32)(0x01)(0x39)(0x07)(0x2b)(0xf8)(0xd9)(0x00)(0x20)
			(0x70)(0xbc)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0xf0)(0xb5)(0x47)(0x46)(0x80)(0xb4)(0xac)(0xb0)(0x0e)(0x1c)(0x00)(0x04)(0x05)(0x0c)(0x12)(0x06)
			(0x12)(0x0e)(0x90)(0x46)(0x03)(0x48)(0x00)(0x68)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x70)(0xb5)(0x00)(0x04)(0x0a)(0x1c)(0x40)(0x0b)(0xe0)(0x21)(0x09)(0x05)(0x41)(0x18)(0x07)(0x31)
			(0x00)(0x23)(0x10)(0x78)(0x08)(0x70)(0x01)(0x33)(0x01)(0x32)(0x01)(0x39)(0x07)(0x2b)(0xf8)(0xd9)
			(0x00)(0x20)(0x70)(0xbc)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>()
	));


// Encompasses FLASH_V120 and V121.
const std::vector<RomPatch> SRAM_PATCHES_FLASH_V12X = boost::assign::list_of
	(RomPatch(
		boost::assign::list_of(0x90)(0xb5)(0x93)(0xb0)(0x6f)(0x46)(0x39)(0x1d)(0x08)(0x1c)(0x00)(0xf0)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of(0x00)(0xb5)(0x3d)(0x20)(0x00)(0x02)(0x1f)(0x21)(0x08)(0x43)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0x80)(0xb5)(0x94)(0xb0)(0x6f)(0x46)(0x39)(0x1c)(0x08)(0x80)(0x38)(0x1c)(0x01)(0x88)(0x0f)(0x29)
			(0x04)(0xd9)(0x01)(0x48)(0x56)(0xe0)(0x00)(0x00)(0xff)(0x80)(0x00)(0x00)(0x23)(0x48)(0x23)(0x49)
			(0x0a)(0x88)(0x23)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x7c)(0xb5)(0x00)(0x07)(0x00)(0x0c)(0xe0)(0x21)(0x09)(0x05)(0x09)(0x18)(0x01)(0x23)(0x1b)(0x03)
			(0xff)(0x20)(0x08)(0x70)(0x01)(0x3b)(0x01)(0x31)(0x00)(0x2b)(0xfa)(0xd1)(0x00)(0x20)(0x7c)(0xbc)
			(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0x80)(0xb5)(0x94)(0xb0)(0x6f)(0x46)(0x79)(0x60)(0x39)(0x1c)(0x08)(0x80)(0x38)(0x1c)(0x01)(0x88)
			(0x0f)(0x29)(0x03)(0xd9)(0x00)(0x48)(0x73)(0xe0)(0xff)(0x80)(0x00)(0x00)(0x38)(0x1c)(0x01)(0x88)
			(0x08)(0x1c)(0xff)(0xf7)(0x21)(0xfe)(0x39)(0x1c)(0x0c)(0x31)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x7c)(0xb5)(0x90)(0xb0)(0x00)(0x03)(0x0a)(0x1c)(0xe0)(0x21)(0x09)(0x05)(0x09)(0x18)(0x01)(0x23)
			(0x1b)(0x03)(0x10)(0x78)(0x08)(0x70)(0x01)(0x3b)(0x01)(0x32)(0x01)(0x31)(0x00)(0x2b)(0xf8)(0xd1)
			(0x00)(0x20)(0x10)(0xb0)(0x7c)(0xbc)(0x08)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>()
	));


// Encompasses FLASH_V123 and V124.
const std::vector<RomPatch> SRAM_PATCHES_FLASH_V12Y = boost::assign::list_of
	(RomPatch(
		boost::assign::list_of(0xff)(0xf7)(0xaa)(0xff)(0x00)(0x04)(0x03)(0x0c)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of(0x1b)(0x23)(0x1b)(0x02)(0x32)(0x20)(0x03)(0x43)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of(0x70)(0xb5)(0x90)(0xb0)(0x15)(0x4d)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of(0x00)(0x20)(0x70)(0x47)(0x15)(0x4d)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		// Patch 3 differs from GBATemp tutorial.
		// The added bytes at the end matter.
		boost::assign::list_of(0x70)(0xb5)(0x46)(0x46)(0x40)(0xb4)(0x90)(0xb0)(0x00)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of(0x00)(0x20)(0x70)(0x47)(0x40)(0xb4)(0x90)(0xb0)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0xf0)(0xb5)(0x90)(0xb0)(0x0f)(0x1c)(0x00)(0x04)(0x04)(0x0c)(0x0f)(0x2c)(0x04)(0xd9)(0x01)(0x48)
			(0x40)(0xe0)(0x00)(0x00)(0xff)(0x80)(0x00)(0x00)(0x20)(0x1c)(0xff)(0xf7)(0xd7)(0xfe)(0x00)(0x04)
			(0x05)(0x0c)(0x00)(0x2d)(0x35)(0xd1)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x70)(0xb5)(0x00)(0x03)(0x0a)(0x1c)(0xe0)(0x21)(0x09)(0x05)(0x41)(0x18)(0x01)(0x23)(0x1b)(0x03)
			(0x10)(0x78)(0x08)(0x70)(0x01)(0x3b)(0x01)(0x32)(0x01)(0x31)(0x00)(0x2b)(0xf8)(0xd1)(0x00)(0x20)
			(0x70)(0xbc)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>()
	));


// FLASH_V125 and FLASH_V126.
const std::vector<RomPatch> SRAM_PATCHES_FLASH_V12Z = boost::assign::list_of
	// FIXME Medabots/Metarot and Super Monkey Ball Jr. (U) don't patch 1:1 with gbata.
	(RomPatch(
		boost::assign::list_of(0xff)(0xf7)(0xaa)(0xff)(0x00)(0x04)(0x03)(0x0c)
			.convert_to_container<std::vector<unsigned char>>(),
			
		boost::assign::list_of(0x1b)(0x23)(0x1b)(0x02)(0x32)(0x20)(0x03)(0x43)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of(0x70)(0xb5)(0x90)(0xb0)(0x15)(0x4d)
			.convert_to_container<std::vector<unsigned char>>(),
		boost::assign::list_of(0x00)(0x20)(0x70)(0x47)(0x15)(0x4d)
			.convert_to_container<std::vector<unsigned char>>()
	))

	// Patch 3 differs from GBATemp tutorial.
	// The added bytes at the end have significance.
	(RomPatch(
		boost::assign::list_of(0x70)(0xb5)(0x46)(0x46)(0x40)(0xb4)(0x90)(0xb0)(0x00)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of(0x00)(0x20)(0x70)(0x47)(0x40)(0xb4)(0x90)(0xb0)(0x00)
			.convert_to_container<std::vector<unsigned char>>()
	))
	(RomPatch(
		boost::assign::list_of
			(0xf0)(0xb5)(0x90)(0xb0)(0x0f)(0x1c)(0x00)(0x04)(0x04)(0x0c)(0x0f)(0x2c)(0x04)(0xd9)(0x01)(0x48)
			(0x40)(0xe0)(0x00)(0x00)(0xff)(0x80)(0x00)(0x00)(0x20)(0x1c)(0xff)(0xf7)(0xd7)(0xfe)(0x00)(0x04)
			(0x05)(0x0c)(0x00)(0x2d)(0x35)(0xd1)
			.convert_to_container<std::vector<unsigned char>>(),
		
		boost::assign::list_of
			(0x70)(0xb5)(0x00)(0x03)(0x0a)(0x1c)(0xe0)(0x21)(0x09)(0x05)(0x41)(0x18)(0x01)(0x23)(0x1b)(0x03)
			(0x10)(0x78)(0x08)(0x70)(0x01)(0x3b)(0x01)(0x32)(0x01)(0x31)(0x00)(0x2b)(0xf8)(0xd1)(0x00)(0x20)
			(0x70)(0xbc)(0x02)(0xbc)(0x08)(0x47)
			.convert_to_container<std::vector<unsigned char>>()
	));


// EEPROM_V111 needs special, calculated patches.
std::vector<ByteOffset> patch_eepromv111(std::vector<unsigned char> & rom_data, const bool interchangeable_empty_byte = true) {
	// The three bytes preceding the last byte of this data need to be amended.
	const std::vector<unsigned char> find1 = boost::assign::list_of(0x0e)(0x48)(0x39)(0x68)(0x01)(0x60)(0x0e)(0x48);
	const std::vector<unsigned char> replacement1 = boost::assign::list_of(0x00)(0x48)(0x00)(0x47)(0)(0)(0)(0x08);
	const std::vector<unsigned char> find2 = boost::assign::list_of(0x27)(0xe0)(0xd0)(0x20)(0x00)(0x05)(0x01)(0x88);
	const std::vector<unsigned char> replacement2 = boost::assign::list_of(0x27)(0xe0)(0xe0)(0x20)(0x00)(0x05)(0x01)(0x88);

	const std::vector<unsigned char> footer = boost::assign::list_of
		(0x39)(0x68)(0x27)(0x48)(0x81)(0x42)(0x23)(0xd0)(0x89)(0x1c)(0x08)(0x88)(0x01)(0x28)(0x02)(0xd1)
		(0x24)(0x48)(0x78)(0x60)(0x33)(0xe0)(0x00)(0x23)(0x00)(0x22)(0x89)(0x1c)(0x10)(0xb4)(0x01)(0x24)
		(0x08)(0x68)(0x20)(0x40)(0x5b)(0x00)(0x03)(0x43)(0x89)(0x1c)(0x52)(0x1c)(0x06)(0x2a)(0xf7)(0xd1)
		(0x10)(0xbc)(0x39)(0x60)(0xdb)(0x01)(0x02)(0x20)(0x00)(0x02)(0x1b)(0x18)(0x0e)(0x20)(0x00)(0x06)
		(0x1b)(0x18)(0x7b)(0x60)(0x39)(0x1c)(0x08)(0x31)(0x08)(0x88)(0x09)(0x38)(0x08)(0x80)(0x16)(0xe0)
		(0x15)(0x49)(0x00)(0x23)(0x00)(0x22)(0x10)(0xb4)(0x01)(0x24)(0x08)(0x68)(0x20)(0x40)(0x5b)(0x00)
		(0x03)(0x43)(0x89)(0x1c)(0x52)(0x1c)(0x06)(0x2a)(0xf7)(0xd1)(0x10)(0xbc)(0xdb)(0x01)(0x02)(0x20)
		(0x00)(0x02)(0x1b)(0x18)(0x0e)(0x20)(0x00)(0x06)(0x1b)(0x18)(0x08)(0x3b)(0x3b)(0x60)(0x0b)(0x48)
		(0x39)(0x68)(0x01)(0x60)(0x0a)(0x48)(0x79)(0x68)(0x01)(0x60)(0x0a)(0x48)(0x39)(0x1c)(0x08)(0x31)
		(0x0a)(0x88)(0x80)(0x21)(0x09)(0x06)(0x0a)(0x43)(0x02)(0x60)(0x07)(0x48)(0x00)(0x47)(0x00)(0x00)
		(0x00)(0x00)(0x00)(0x0d)(0x00)(0x00)(0x00)(0x0e)(0x04)(0x00)(0x00)(0x0e)(0xd4)(0x00)(0x00)(0x04)
		(0xd8)(0x00)(0x00)(0x04)(0xdc)(0x00)(0x00)(0x04)(0)(0)(0)(0x08);

	const size_t rom_eod = find_rom_eod(rom_data, interchangeable_empty_byte);
	const size_t footer_offset = next_aligned_address(rom_eod+1, 16);

	std::vector<ByteOffset> results;

	ByteOffset replace1_results = replace_bytes(rom_data, find1, replacement1);
	ByteOffset replace2_results = replace_bytes(rom_data, find2, replacement2); // Second patch is just a normal patch.

	results.push_back(replace1_results);
	results.push_back(replace2_results);

	if (replace1_results.valid) {
		size_t off1 = replace1_results.offset;
		int32_t _footer_off = (int32_t) footer_offset;
		int32_t _off1 = (int32_t) off1;

		// http://esr.ibiblio.org/?p=5095
		bool is_big_endian = *(uint16_t *) "\0\xff" < 0x100;

		// Ensure there's enough room for the footer.
		rom_data.reserve(std::max(rom_data.size(), footer_offset+1));
		rom_data.resize(std::max(rom_data.size(), footer_offset+1));

		// Write footer.
		for (size_t i=0; i < footer.size(); i++) {
			rom_data[footer_offset+i] = footer[i];
		}

		results.push_back(ByteOffset(true, footer_offset));

		// Amend first patch.
		if (!is_big_endian) {
			rom_data[off1 + 4] = (unsigned char) (((_footer_off + 1) >> (8 * 0)) & 0xff);
			rom_data[off1 + 5] = (unsigned char) (((_footer_off + 1) >> (8 * 1)) & 0xff);
			rom_data[off1 + 6] = (unsigned char) (((_footer_off + 1) >> (8 * 2)) & 0xff);
		} else {
			rom_data[off1 + 4] = (unsigned char) (((_footer_off + 1) >> (8 * 3)) & 0xff);
			rom_data[off1 + 5] = (unsigned char) (((_footer_off + 1) >> (8 * 2)) & 0xff);
			rom_data[off1 + 6] = (unsigned char) (((_footer_off + 1) >> (8 * 1)) & 0xff);
		}

		results.push_back(ByteOffset(true, off1));

		// Amend footer patch.
		if (!is_big_endian) {
			rom_data[footer_offset + 184] = (unsigned char) (((_off1 + 33) >> (8 * 0)) & 0xff);
			rom_data[footer_offset + 185] = (unsigned char) (((_off1 + 33) >> (8 * 1)) & 0xff);
			rom_data[footer_offset + 186] = (unsigned char) (((_off1 + 33) >> (8 * 2)) & 0xff);
		} else {
			rom_data[footer_offset + 184] = (unsigned char) (((_off1 + 33) >> (8 * 3)) & 0xff);
			rom_data[footer_offset + 185] = (unsigned char) (((_off1 + 33) >> (8 * 2)) & 0xff);
			rom_data[footer_offset + 186] = (unsigned char) (((_off1 + 33) >> (8 * 1)) & 0xff);
		}

		results.push_back(ByteOffset(true, footer_offset));
	} else {
		throw PatternNotFoundException("Failed to find leading pattern in ROM for EEPROM_V111 to SRAM patch. Cannot write supplement or footer patch.");
	}

	return results;
};


std::vector<ByteOffset> patch_sram_by_set(std::vector<unsigned char> & rom_data, const std::vector<RomPatch> & patch_set) {
	std::vector<ByteOffset> results;

	for (const RomPatch & patch : patch_set) {
		results.push_back(replace_bytes(rom_data, patch.find_data, patch.replacement_data, &patch.find_mask, &patch.replacement_mask));
	}

	return results;
}


std::vector<ByteOffset> patch_sram_by_type(std::vector<unsigned char> & rom_data, const gba::SaveType save_type,
						const bool interchangeable_empty_byte) {
	std::vector<ByteOffset> results;

	switch (save_type) {
		case gba::FLASH_V120:
		case gba::FLASH_V121:
			results = patch_sram_by_set(rom_data, SRAM_PATCHES_FLASH_V12X);
			break;

		case gba::FLASH_V123:
		case gba::FLASH_V124:
			results = patch_sram_by_set(rom_data, SRAM_PATCHES_FLASH_V12Y);
			break;

		case gba::FLASH_V125:
		case gba::FLASH_V126:
			results = patch_sram_by_set(rom_data, SRAM_PATCHES_FLASH_V12Z);
			break;

		case gba::FLASH512_V130:
		case gba::FLASH512_V131:
		case gba::FLASH512_V133:
			results = patch_sram_by_set(rom_data, SRAM_PATCHES_FLASH512_V13X);
			break;

		case gba::FLASH1M_V102:
			results = patch_sram_by_set(rom_data, SRAM_PATCHES_FLASH1M_V102);
			break;

		case gba::FLASH1M_V103:
			results = patch_sram_by_set(rom_data, SRAM_PATCHES_FLASH1M_V103);
			break;

		case gba::EEPROM_V111:
			results = patch_eepromv111(rom_data, interchangeable_empty_byte);
			break;

		case gba::EEPROM_V120:
		case gba::EEPROM_V121:
		case gba::EEPROM_V122:
			results = patch_sram_by_set(rom_data, SRAM_PATCHES_EEPROM_V12X);
			break;

		case gba::EEPROM_V124:
			results = patch_sram_by_set(rom_data, SRAM_PATCHES_EEPROM_V124);
			break;

		case gba::EEPROM_V126:
			results = patch_sram_by_set(rom_data, SRAM_PATCHES_EEPROM_V126);
			break;

		case gba::NO_SAVE:
		case gba::SRAM_V110:
		case gba::SRAM_V112:
		case gba::SRAM_V111:
		case gba::SRAM_V113:
		case gba::FRAM_V100:
		case gba::FRAM_V102:
		case gba::FRAM_V103:
		case gba::FRAM_V110:
			break;
	}

	return results;
}


std::vector<ByteOffset> patch_sram(std::vector<unsigned char> &rom_data) {
	std::vector<ByteOffset> results;

	for (const gba::SaveType & save_type : gba::SAVE_TYPES) {
		const std::vector<unsigned char> pattern = gba::SAVE_TYPE_BYTE_PATTERNS.at(save_type);

		if (pattern.size() > 0 && find_bytes(rom_data, pattern)) {
			std::vector<ByteOffset> foo = patch_sram_by_type(rom_data, save_type);
			results.insert(results.end(), foo.begin(), foo.end());
		}
	}

	return results;
}
