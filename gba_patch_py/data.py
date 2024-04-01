# coding=utf-8

from typing import Literal


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
