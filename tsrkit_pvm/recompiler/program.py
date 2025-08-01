from typing import Dict, List, Tuple, Union
from tsrkit_types.bits import Bits
from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable

from tsrkit_pvm.recompiler.vm_context import VMContext, gas_offset

from ..interpreter.constants import PVM_ADDR_ALIGNMENT
from .assembler.inst_map import inst_map
from ..interpreter.status import CONTINUE, HALT, PANIC, ExecutionStatus, PvmError
from tsrkit_asm import Condition, ImmKind, MemOp, Operands, PyAssembler, Reg, RegMem, RegSize


class AssemblerContext:
    """Wrapper for Assembler to contain labels"""
    asm: PyAssembler
    labels: Dict[int, int]
    halt_label: int
    panic_label: int
    jump_table_len: int

    def __init__(self, assembler, labels, halt_label, panic_label, jump_table_len):
        self.asm = assembler
        self.labels = labels
        self.halt_label = halt_label 
        self.panic_label = panic_label
        self.jump_table_len = jump_table_len

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
            if self.offset_bitmask[n] and inst_map.is_terminating(
                self.instruction_set[n]
            ):
                basic_blocks.append(n + 1 + self._skip_cache[n])

        self.basic_blocks = basic_blocks
        self.zeta = bytearray(self.instruction_set) + bytes(100)
        self._basic_blocks_set = set(self.basic_blocks)

    def assemble(self, program_counter: int, logger = None) -> Tuple[bytes, int, List[int]]:
        asm = PyAssembler()

        # Create labels for all basic blocks (jump targets)
        labels = {}
        for i in range(len(self.instruction_set)):
            if self.offset_bitmask[i]:
                labels[i] = asm.forward_declare_label()
        
        halt_label = asm.forward_declare_label()
        panic_label = asm.forward_declare_label()
        # Create context wrapper
        asm_ctx = AssemblerContext(asm, labels, halt_label, panic_label, len(self.jump_table))

        insts = set()

        counter = 0
        msn_pc_offset = 0
        jump_table = self.jump_table
        while counter < len(self.instruction_set):
            if counter == program_counter:
                msn_pc_offset = asm.len()
            if self.offset_bitmask[counter]:  # Only process actual opcodes
                # Define label if this is a basic block start
                if counter in labels:
                    asm.define_label(labels[counter])
                    if counter in jump_table:
                        jump_table[jump_table.index(counter)] = asm.current_address()

                opcode = self.instruction_set[counter]
                if logger: logger.debug(f"📍 {counter} \t Processing opcode \t {inst_map._dispatch_table[opcode].fn.__name__} ({opcode})")
                gas = inst_map.assemble_instruction(opcode, self, counter, asm_ctx)
                
                # --- Gas Computation --- #
                x61mov_imm = -gas_offset + 0x61
                asm.sub(Operands.RegMem_Imm(RegMem.Reg(Reg.r15), ImmKind.I64(x61mov_imm)))
                asm.sub(
                    Operands.RegMem_Imm(
                        RegMem.Mem(
                            MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=0x61)
                        ),
                        ImmKind.I32(gas)
                    )
                )
                asm.jcc_rel32(Condition.Sign, -2)
                asm.add(Operands.RegMem_Imm(RegMem.Reg(Reg.r15), ImmKind.I64(x61mov_imm)))

                insts.add(inst_map._dispatch_table[opcode].fn.__name__)
            counter += 1

        if logger: logger.debug(f"🧩 Assembled instructions: {insts}")
        
        # If normally returned, then its a panic 
        asm.define_label(panic_label)
        panic_addr = asm.current_address()
        asm.ret()

        # Add a block for HALT exit
        asm.define_label(halt_label)
        halt_addr = asm.current_address()
        # Jump to memory, which is non-executable and will throw seg fault
        asm.ud2()

        if logger: logger.debug(f"🧩 Assembled program size: {asm.len()} | Starting PC offset: {msn_pc_offset}")

        return asm.finalize(), msn_pc_offset, jump_table, panic_addr, halt_addr

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
        return (
            self.z == other.z
            and self.jump_table == other.jump_table
            and self.instruction_set == other.instruction_set
            and self.offset_bitmask == other.offset_bitmask
        )
