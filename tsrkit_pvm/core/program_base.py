from typing import List, Union, Tuple
from dataclasses import dataclass, field
from tsrkit_types import Bits, Uint
from tsrkit_pvm.common.extended import ExtendedList


@dataclass
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
    basic_blocks: List[int] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        # Pre-compute and cache frequently accessed values
        self._extended_bitmask = self.offset_bitmask + [True] * 1000 # ExtendedList(self.offset_bitmask, default=True)
        self.zeta = self.instruction_set + bytes([0] * 1000) # ExtendedList(self.instruction_set, default=0)

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
        return int(total_size)

    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        """Encode the program bytecode into a buffer.

        Args:
            buffer: The buffer to encode the program into
            offset: Offset of the buffer to start encoding from
        """
        total_size = self.encode_size()
        # self._check_buffer_size(buffer, total_size, offset)  # TODO: Implement if needed
        current_offset = offset
        size = Uint[8](len(self.jump_table)).encode_into(buffer, current_offset)
        current_offset += size
        size = Uint[8](self.z).encode_into(buffer, current_offset)
        current_offset += size
        size = Uint(len(self.instruction_set)).encode_into(buffer, current_offset)
        current_offset += size
        JumpInt = Uint[self.z * 8]
        for jump in self.jump_table:
            size = JumpInt(jump).encode_into(buffer, current_offset)
            current_offset += size

        buffer[current_offset : current_offset + len(self.instruction_set)] = (
            self.instruction_set
        )
        current_offset += len(self.instruction_set)
        size = Bits[len(self.instruction_set), "lsb"](self.offset_bitmask).encode_into(
            buffer, current_offset
        )
        current_offset += size
        return int(current_offset - offset)

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

        z, size = int.from_bytes(buffer[current_offset : current_offset + 1], "little"), 1
        bytes_read += size
        current_offset += size
        
        c_len, size = Uint.decode_from(buffer, current_offset)
        bytes_read += size
        current_offset += size
        
        j: List = []
        for _ in range(j_len):
            val = int.from_bytes(buffer[current_offset : current_offset + z], "little")
            bytes_read += z
            current_offset += z
            j.append(int(val))

        c = bytes(buffer[current_offset : current_offset + c_len])
        current_offset += c_len

        # Optimized bit decoding with minimal operations
        bit_bytes_needed = (c_len + 7) // 8
        bit_data = buffer[current_offset : current_offset + bit_bytes_needed]
        
        # Pre-allocate list with exact size for better performance
        offset_bitmask = [False] * c_len
        
        # Process bits 8 at a time when possible
        full_bytes = c_len // 8
        for byte_idx in range(full_bytes):
            byte_val = bit_data[byte_idx] if byte_idx < len(bit_data) else 0
            base_idx = byte_idx << 3  # Equivalent to byte_idx * 8, but faster
            
            # Unrolled bit extraction for maximum speed
            offset_bitmask[base_idx] = bool(byte_val & 1)
            offset_bitmask[base_idx + 1] = bool(byte_val & 2)
            offset_bitmask[base_idx + 2] = bool(byte_val & 4)
            offset_bitmask[base_idx + 3] = bool(byte_val & 8)
            offset_bitmask[base_idx + 4] = bool(byte_val & 16)
            offset_bitmask[base_idx + 5] = bool(byte_val & 32)
            offset_bitmask[base_idx + 6] = bool(byte_val & 64)
            offset_bitmask[base_idx + 7] = bool(byte_val & 128)
        
        # Handle remaining bits
        remaining_bits = c_len & 7  # Equivalent to c_len % 8, but faster
        if remaining_bits and full_bytes < len(bit_data):
            byte_val = bit_data[full_bytes]
            base_idx = full_bytes << 3
            for bit_idx in range(remaining_bits):
                offset_bitmask[base_idx + bit_idx] = bool(byte_val & (1 << bit_idx))
        
        bytes_read += bit_bytes_needed
        current_offset += bit_bytes_needed

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

    def __repr__(self) -> str:
        return f"Program(z={self.z}, jump_table={self.jump_table}, instruction_set={self.instruction_set!r}, offset_bitmask={self.offset_bitmask})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Program):
            return NotImplemented
        return (
            self.z == other.z
            and self.jump_table == other.jump_table
            and self.instruction_set == other.instruction_set
            and self.offset_bitmask == other.offset_bitmask
        )
