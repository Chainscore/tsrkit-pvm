from dataclasses import field
from typing import List, Union, Tuple
from tsrkit_types import Bits, Uint, structure
from tsrkit_pvm.common.extended import ExtendedList


@structure
class Program:
    """
    Abstract base class for Program implementations.

    Args:
        z: Size of jump-table entries
        jump_table: sequence of NN, each of size z
        instruction_set: Sequence of instructions (U8)
        offset_bitmask: Bitsequence of size len(instruction_set) that defines which blob is an opcode
    """

    z: int
    jump_table: List
    instruction_set: bytes
    offset_bitmask: List

    def __post_init__(self):
        # Pre-compute and cache frequently accessed values
        self._extended_bitmask = ExtendedList(self.offset_bitmask, default=True)
        self.zeta = ExtendedList(self.instruction_set, default=0)

    def skip(self, pc: int) -> int:
        """Calculate skip value for instruction at pc. Default implementation returns 0."""
        raise NotImplementedError("skip method must be implemented in subclass")

    def encode_size(self) -> int:
        """Encode the size of the program.

        Returns:
            int: Size of the program
        """
        total_size = 0
        total_size += Uint(len(self.jump_table)).encode_size()
        total_size += 1
        total_size += Uint(len(self.instruction_set)).encode_size()
        for jump in self.jump_table:
            total_size += Uint[self.z * 8](jump).encode_size()
        total_size += len(self.instruction_set)
        total_size += Bits[len(self.instruction_set)](self.offset_bitmask).encode_size()
        return total_size

    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        """Encode the program bytecode into a buffer.

        Args:
            buffer: The buffer to encode the program into
            offset: Offset of the buffer to start encoding from
        """
        total_size = self.encode_size()
        self._check_buffer_size(buffer, total_size, offset)
        current_offset = offset
        size = Uint[8](len(self.jump_table)).encode_into(buffer, current_offset)
        current_offset += size
        size = Uint[8](self.z).encode_into(buffer, current_offset)
        current_offset += size
        size = Uint(len(self.instruction_set)).encode_into(buffer, current_offset)
        current_offset += size
        for jump in self.jump_table:
            size = Uint[self.z * 8](jump).encode_into(buffer, current_offset)
            current_offset += size

        buffer[current_offset : current_offset + len(self.instruction_set)] = (
            self.instruction_set
        )
        current_offset += len(self.instruction_set)
        size = Bits[len(self.instruction_set), "lsb"](self.offset_bitmask).encode_into(
            buffer, current_offset
        )
        current_offset += size
        return current_offset - offset

    @classmethod
    def decode_from(
        cls, buffer: Union[bytes, bytearray], offset: int = 0
    ) -> Tuple["Program", int]:
        """Decode a program from a bytes

        Args:
            buffer (Union[bytes, bytearray]): Bytes
            offset (int, optional): Where to start decoding from. Defaults to 0.

        Returns:
            Tuple[Self, int]: Returns Program and bytes read

        TODO: Implement conditions - https://graypaper.fluffylabs.dev/#/68eaa1f/234701234701?v=0.6.4
        """
        current_offset = offset
        bytes_read = 0

        j_len, size = Uint.decode_from(buffer, current_offset)
        bytes_read += size
        current_offset += size

        z, size = Uint[8].decode_from(buffer, current_offset)
        bytes_read += size
        current_offset += size

        c_len, size = Uint.decode_from(buffer, current_offset)
        bytes_read += size
        current_offset += size

        j: List = []
        for _ in range(j_len):
            val, size = Uint[z * 8].decode_from(buffer, current_offset)
            bytes_read += size
            current_offset += size
            j.append(int(val))

        c = buffer[current_offset : current_offset + c_len]
        current_offset += c_len

        offset_bitmask, size = Bits[c_len, "lsb"].decode_from(buffer, current_offset)
        bytes_read += size
        current_offset += size

        return cls(int(z), j, c, list(offset_bitmask)), bytes_read

    @classmethod
    def from_json(cls, data: Union[bytes, bytearray]) -> "Program":
        """Decode a program from a bytes

        Args:
            buffer (Union[bytes, bytearray]): Bytes

        Returns:
            Tuple[Self, int]: Returns Program and bytes read
        """
        value, _ = Program.decode_from(data)
        return value

    def __repr__(self):
        return f"Program(z={self.z}, jump_table={self.jump_table}, instruction_set={self.instruction_set}, offset_bitmask={self.offset_bitmask})"

    def __eq__(self, other):
        return (
            self.z == other.z
            and self.jump_table == other.jump_table
            and self.instruction_set == other.instruction_set
            and self.offset_bitmask == other.offset_bitmask
        )
