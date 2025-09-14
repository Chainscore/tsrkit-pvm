from typing import Any, Callable, Dict, TYPE_CHECKING

from tsrkit_pvm.recompiler.assembler.utils import pop_all_regs, save_all_regs

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program

from ...vm_context import r_map, TEMP_REG

from tsrkit_asm import RegSize, Operands, RegMem, Reg, ImmKind, Size


class InstructionsWArgs2Reg(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index


    def get_props(self):
        rd = min(12, self.program.zeta[self.counter + 1] % 16)
        ra = min(12, self.program.zeta[self.counter + 1] // 16)
        return (rd, ra)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            100: OpCode(name="move_reg", fn=cls.move_reg, gas=1, is_terminating=False),
            101: OpCode(name="sbrk", fn=cls.sbrk, gas=1, is_terminating=False),
            102: OpCode(
                name="count_set_bits_64",
                fn=cls.count_set_bits_64,
                gas=1,
                is_terminating=False,
            ),
            103: OpCode(
                name="count_set_bits_32",
                fn=cls.count_set_bits_32,
                gas=1,
                is_terminating=False,
            ),
            104: OpCode(
                name="leading_zero_bits_64",
                fn=cls.leading_zero_bits_64,
                gas=1,
                is_terminating=False,
            ),
            105: OpCode(
                name="leading_zero_bits_32",
                fn=cls.leading_zero_bits_32,
                gas=1,
                is_terminating=False,
            ),
            106: OpCode(
                name="trailing_zero_bits_64",
                fn=cls.trailing_zero_bits_64,
                gas=1,
                is_terminating=False,
            ),
            107: OpCode(
                name="trailing_zero_bits_32",
                fn=cls.trailing_zero_bits_32,
                gas=1,
                is_terminating=False,
            ),
            108: OpCode(
                name="sign_extend_8", fn=cls.sign_extend_8, gas=1, is_terminating=False
            ),
            109: OpCode(
                name="sign_extend_16",
                fn=cls.sign_extend_16,
                gas=1,
                is_terminating=False,
            ),
            110: OpCode(
                name="zero_extend_16",
                fn=cls.zero_extend_16,
                gas=1,
                is_terminating=False,
            ),
            111: OpCode(
                name="reverse_bytes", fn=cls.reverse_bytes, gas=1, is_terminating=False
            ),
        }

    def move_reg(self, asm, rd: int, ra: int):
        """rd = ra (register move)"""
        if ra != rd:
            asm.mov(RegSize.R64, r_map[rd], r_map[ra])

    def sbrk(self, asm, rd: int, ra: int):
        """rd = old_heap_break; heap_break += ra (PVM sbrk syscall)"""
        PVM_SYS_SBRK = 999
        # Save all regs before exiting
        save_all_regs(asm)
        pop_all_regs(asm)  # This is safe to do so, not doing this also works
        # Load rax in rcx
        asm.mov_imm64(Reg.rax, PVM_SYS_SBRK)
        asm.syscall()

    def count_set_bits_64(self, asm, rd: int, ra: int):
        """rd = popcount(ra) (count number of 1 bits in 64-bit value)"""
        # Use x86 POPCNT instruction if available, otherwise use a loop
        asm.popcnt(RegSize.R64, r_map[rd], RegMem.Reg(r_map[ra]))

    def count_set_bits_32(self, asm, rd: int, ra: int):
        """rd = count_set_bits(ra) (32-bit)"""
        asm.mov(size=RegSize.R32, a=TEMP_REG, b=r_map[ra])
        asm.popcnt(RegSize.R32, r_map[rd], RegMem.Reg(TEMP_REG))
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])

    def leading_zero_bits_64(self, asm, rd: int, ra: int):
        """rd = lzcnt(ra) (count leading zero bits in 64-bit value)"""
        # Use x86 LZCNT instruction
        asm.lzcnt(RegSize.R64, r_map[rd], RegMem.Reg(r_map[ra]))

    def leading_zero_bits_32(self, asm, rd: int, ra: int):
        """rd = count_leading_zeros(ra) (32-bit)"""
        # lzcnt is undefined for an input of 0. The ISA specifies that for an input of 0,
        # the output should be the operand size (32).
        asm.mov(size=RegSize.R32, a=TEMP_REG, b=r_map[ra])
        asm.mov_imm64(r_map[rd], 32)
        asm.lzcnt(RegSize.R32, r_map[rd], RegMem.Reg(TEMP_REG))
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])

    def trailing_zero_bits_64(self, asm, rd: int, ra: int):
        """rd = tzcnt(ra) (count trailing zero bits in 64-bit value)"""
        # Use x86 TZCNT instruction (or BSF as fallback)
        asm.tzcnt(RegSize.R64, r_map[rd], RegMem.Reg(r_map[ra]))

    def trailing_zero_bits_32(self, asm, rd: int, ra: int):
        """rd = count_trailing_zeros(ra) (32-bit)"""
        # tzcnt is undefined for an input of 0. The ISA specifies that for an input of 0,
        # the output should be the operand size (32).
        # We use a temporary register (rcx) to handle this case.
        asm.mov(size=RegSize.R32, a=TEMP_REG, b=r_map[ra])
        asm.mov_imm64(r_map[rd], 32)
        asm.tzcnt(RegSize.R32, r_map[rd], RegMem.Reg(TEMP_REG))
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])

    def sign_extend_8(self, asm, rd: int, ra: int):
        """rd = sign_extend_8(ra) (sign extend 8-bit value to 64-bit)"""
        # Use MOVSX to sign extend from 8-bit to 64-bit
        asm.movsx_8_to_64(RegSize.R64, r_map[rd], r_map[ra])

    def sign_extend_16(self, asm, rd: int, ra: int):
        """rd = sign_extend_16(ra) (sign extend 16-bit value to 64-bit)"""
        # Use MOVSX to sign extend from 16-bit to 64-bit
        asm.movsx_16_to_64(RegSize.R64, r_map[rd], r_map[ra])

    def zero_extend_16(self, asm, rd: int, ra: int):
        """rd = zero_extend_16(ra) (zero extend 16-bit value to 64-bit)"""
        # Use MOVZX to zero extend from 16-bit to 64-bit
        asm.movzx_16_to_64(RegSize.R64, r_map[rd], r_map[ra])

    def reverse_bytes(self, asm, rd: int, ra: int):
        """rd = bswap(ra) (reverse byte order of 64-bit value)"""
        # Copy ra to rd first, then byte swap in place
        asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
        # Use BSWAP to reverse byte order
        asm.bswap(RegSize.R64, r_map[rd])
