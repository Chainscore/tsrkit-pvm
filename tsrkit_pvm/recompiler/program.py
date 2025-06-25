from math import floor
from typing import Dict, List, Tuple, Union

from tsrkit_types.bits import Bits
from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable

from ..interpreter.constants import PVM_ADDR_ALIGNMENT
from .assembler.inst_map import inst_map
from ..interpreter.status import CONTINUE, HALT, PANIC, ExecutionStatus, PvmError
from py_asm import *
from py_asm import LOAD_U64


class AssemblerContext:
    """Wrapper for Assembler to contain labels"""
    def __init__(self, assembler, labels):
        self.asm = assembler
        self.labels = labels
    
    def __getattr__(self, name):
        # Delegate all other attributes to the underlying assembler
        return getattr(self.asm, name)


class Program(Codable):
    """This is the program blob which the PVM will execute.

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
    basic_blocks: List

    # Cache frequently accessed values
    _offset_bitmask_len: int
    _extended_bitmask: List[bool]
    _extended_bitmask_len: int
    _jump_table_len: int
    _jump_table_max_addr: int
    _skip_cache: Dict[int, int]

    def __init__(
        self,
        z: int,
        jump_table: List[int],
        instruction_set: bytes,
        offset_bitmask: List[bool],
    ):
        self.z = z
        self.jump_table = jump_table
        self.instruction_set = instruction_set
        self.offset_bitmask = offset_bitmask
        
        # Pre-compute and cache frequently accessed values
        self._offset_bitmask_len = len(self.offset_bitmask)
        self._extended_bitmask = self.offset_bitmask + [True] * 10  # Compute once
        self._extended_bitmask_len = len(self._extended_bitmask)
        self._jump_table_len = len(self.jump_table)
        self._jump_table_max_addr = self._jump_table_len * PVM_ADDR_ALIGNMENT
        
        # Pre-compute skip values for all positions to eliminate runtime calculation
        self._skip_cache: Dict[int, int] = {}
        self._precompute_skip_values()
        
        # Build basic blocks using cached skip values
        basic_blocks = [0]
        for n in range(len(self.instruction_set)):
            if (
                    self.offset_bitmask[n] and
                    inst_map.is_terminating(self.instruction_set[n])
            ):
                basic_blocks.append(n + 1 + self._skip_cache.get(n, 0))
        
        self.basic_blocks = basic_blocks
        self.zeta = bytearray(self.instruction_set) + bytes(100)
        self._basic_blocks_set = set(self.basic_blocks)


    def assemble(self, program_counter: int) -> Tuple[bytes, int]:
        asm = PyAssembler()
        
        # Create labels for all basic blocks (jump targets)
        labels = {}
        for block_start in self.basic_blocks:
            if block_start < len(self.instruction_set):
                labels[block_start] = asm.forward_declare_label()
        
        # Create context wrapper
        asm_ctx = AssemblerContext(asm, labels)

        counter = 0
        msn_pc_offset = 0 
        while counter < len(self.instruction_set):
            if counter == program_counter:
                msn_pc_offset = asm.len()
            if self.offset_bitmask[counter]:  # Only process actual opcodes
                # Define label if this is a basic block start
                if counter in labels:
                    asm.define_label(labels[counter])
                    
                opcode = self.instruction_set[counter]
                print(f"Running opcode {opcode} at position {counter}")
                inst_map.assemble_instruction(opcode, self, counter, asm_ctx)
            counter += 1

        asm.ret()

        return asm.finalize(), msn_pc_offset


    def _precompute_skip_values(self):
        """Pre-compute skip values for all positions to eliminate runtime overhead."""
        for i in range(self._offset_bitmask_len):
            skip_value = self._extended_bitmask_len 
            for j in range(i + 1, self._extended_bitmask_len):
                if self._extended_bitmask[j]:
                    skip_value = j - i - 1
                    break
            
            self._skip_cache[i] = min(24, skip_value)

    def skip(self, pc) -> int:
        """
        Skip the instructions until the next opcode is found.
        Args:
            pc: Current index
        Returns:
            Distance to the next opcode.
        """
        return self._skip_cache.get(pc, 0)

    def branch(
        self,
        counter: int,
        branch: int,
        condition: bool
    ) -> Tuple[ExecutionStatus, int]:
        if not condition:
            return CONTINUE, counter
        elif branch not in self._basic_blocks_set:
            raise PvmError(PANIC)
        return CONTINUE, branch

    def djump(
        self, 
        counter: int,
        a: int
    ) -> Tuple[ExecutionStatus, int]:
        if a == 2**32 - 2**16:
            return HALT, counter
        elif (
            a == 0 or
            a > self._jump_table_max_addr or
            a % PVM_ADDR_ALIGNMENT != 0 or
            self.jump_table[floor(a//PVM_ADDR_ALIGNMENT) - 1] not in self._basic_blocks_set
        ):
            raise PvmError(PANIC)
        return CONTINUE, self.jump_table[floor(a//PVM_ADDR_ALIGNMENT) - 1]

    def encode_size(self) -> int:
        """Encode the size of the program.

        Returns:
            int: Size of the program
        """
        total_size = 0
        total_size += Uint(self._jump_table_len).encode_size()
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
        size = Uint[8](self._jump_table_len).encode_into(buffer, current_offset)
        current_offset += size
        size = Uint[8](self.z).encode_into(buffer, current_offset)
        current_offset += size
        size = Uint(len(self.instruction_set)).encode_into(
            buffer, current_offset
        )
        current_offset += size
        for jump in self.jump_table:
            size = Uint[self.z * 8](jump).encode_into(buffer, current_offset)
            current_offset += size

        buffer[current_offset:current_offset+len(self.instruction_set)] = self.instruction_set
        current_offset+=len(self.instruction_set)
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

        c = buffer[current_offset:current_offset+c_len]
        current_offset += c_len

        offset_bitmask, size = Bits[c_len, "lsb"].decode_from(
            buffer, current_offset
        )
        bytes_read += size
        current_offset += size

        return Program(int(z), j, c, list(offset_bitmask)), bytes_read

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
        return self.z == other.z and self.jump_table == other.jump_table and self.instruction_set == other.instruction_set and self.offset_bitmask == other.offset_bitmask
