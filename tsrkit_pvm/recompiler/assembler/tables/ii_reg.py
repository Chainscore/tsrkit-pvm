from typing import Any, Callable, Dict, TYPE_CHECKING

from ..instruction_table import InstructionTable
from ..opcode import OpCode
from ...vm_context import r_map

from tsrkit_asm import RegSize, Operands, RegMem, Reg, ImmKind


class InstructionsWArgs2Reg(InstructionTable):
    @property
    def rd(self) -> int:
        return min(12, self.program.zeta[self.counter + 1] % 16)

    @property
    def ra(self) -> int:
        return min(12, self.program.zeta[self.counter + 1] // 16)

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

    def move_reg(self, asm):
        """rd = ra (register move)"""
        if self.ra != self.rd:
            asm.mov(RegSize.R64, r_map[self.rd], r_map[self.ra])

    def sbrk(self, asm):
        """rd = heap_break; heap_break += ra (system break/memory allocation)"""
        # This is a complex system call - for now just move ra to rd as placeholder
        # In a real implementation, this would need to interact with memory management
        asm.mov(size=RegSize.R64, a=r_map[self.rd], b=r_map[self.ra])
        # TODO: Implement proper heap management

    def count_set_bits_64(self, asm):
        """rd = popcount(ra) (count number of 1 bits in 64-bit value)"""
        # Use x86 POPCNT instruction if available, otherwise use a loop
        asm.popcnt(r_map[self.rd], RegMem.Reg(r_map[self.ra]))

    def count_set_bits_32(self, asm):
        """rd = popcount(ra & 0xFFFFFFFF) (count number of 1 bits in lower 32 bits)"""
        # Mask to 32 bits then count
        asm.mov(
            size=RegSize.R32, a=r_map[self.rd], b=r_map[self.ra]
        )  # Auto-zeros upper 32 bits
        asm.popcnt(r_map[self.rd], RegMem.Reg(r_map[self.rd]))

    def leading_zero_bits_64(self, asm):
        """rd = lzcnt(ra) (count leading zero bits in 64-bit value)"""
        # Use x86 LZCNT instruction
        asm.lzcnt(r_map[self.rd], RegMem.Reg(r_map[self.ra]))

    def leading_zero_bits_32(self, asm):
        """rd = lzcnt(ra & 0xFFFFFFFF) (count leading zero bits in lower 32 bits)"""
        # Mask to 32 bits then count leading zeros
        asm.mov(
            size=RegSize.R32, a=r_map[self.rd], b=r_map[self.ra]
        )  # Auto-zeros upper 32 bits
        asm.lzcnt(r_map[self.rd], RegMem.Reg(r_map[self.rd]))

    def trailing_zero_bits_64(self, asm):
        """rd = tzcnt(ra) (count trailing zero bits in 64-bit value)"""
        # Use x86 TZCNT instruction (or BSF as fallback)
        asm.tzcnt(r_map[self.rd], RegMem.Reg(r_map[self.ra]))

    def trailing_zero_bits_32(self, asm):
        """rd = tzcnt(ra & 0xFFFFFFFF) (count trailing zero bits in lower 32 bits)"""
        # Mask to 32 bits then count trailing zeros
        asm.mov(
            size=RegSize.R32, a=r_map[self.rd], b=r_map[self.ra]
        )  # Auto-zeros upper 32 bits
        asm.tzcnt(r_map[self.rd], RegMem.Reg(r_map[self.rd]))

    def sign_extend_8(self, asm):
        """rd = sign_extend_8(ra) (sign extend 8-bit value to 64-bit)"""
        # Use MOVSX to sign extend from 8-bit to 64-bit
        asm.movsx(
            size=RegSize.R64, reg=r_map[self.rd], reg_mem=RegMem.Reg(r_map[self.ra])
        )

    def sign_extend_16(self, asm):
        """rd = sign_extend_16(ra) (sign extend 16-bit value to 64-bit)"""
        # Use MOVSX to sign extend from 16-bit to 64-bit
        asm.movsx(
            size=RegSize.R64, reg=r_map[self.rd], reg_mem=RegMem.Reg(r_map[self.ra])
        )

    def zero_extend_16(self, asm):
        """rd = zero_extend_16(ra) (zero extend 16-bit value to 64-bit)"""
        # Use MOVZX to zero extend from 16-bit to 64-bit
        asm.movzx(
            size=RegSize.R64, reg=r_map[self.rd], reg_mem=RegMem.Reg(r_map[self.ra])
        )

    def reverse_bytes(self, asm):
        """rd = bswap(ra) (reverse byte order of 64-bit value)"""
        # Copy ra to rd first, then byte swap in place
        asm.mov(size=RegSize.R64, a=r_map[self.rd], b=r_map[self.ra])
        # Use BSWAP to reverse byte order
        asm.bswap(r_map[self.rd])
