from typing import Any, Callable, Dict, TYPE_CHECKING

from ..instruction_table import InstructionTable
from ..opcode import OpCode
from ...vm_context import r_map

from tsrkit_asm import (
    Reg,
    RegSize,
    Size,
    MemOp,
    PyAssembler
)


class InstructionsWArgs1Reg2Imm(InstructionTable):
    @property
    def ra(self) -> int:
        return min(12, self.program.zeta[self.counter + 1] % 16)

    @property
    def lx(self) -> int:
        return min(4, (self.program.zeta[self.counter + 1] // 16) % 8)

    @property
    def ly(self) -> int:
        return min(4, max(0, int(self.skip_index) - self.lx - 1))

    @property
    def vx(self) -> int:
        start = self.counter + 2
        end = start + self.lx
        return int.from_bytes(self.program.zeta[start:end], "little", signed=False)

    @property
    def vy(self) -> int:
        start = self.counter + 2 + self.lx
        end = start + self.ly
        return int.from_bytes(self.program.zeta[start:end], "little", signed=False)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            70: OpCode("store_imm_ind_u8", cls.store_imm_ind(8), 1, False),
            71: OpCode("store_imm_ind_u16", cls.store_imm_ind(16), 1, False),
            72: OpCode("store_imm_ind_u32", cls.store_imm_ind(32), 1, False),
            73: OpCode("store_imm_ind_u64", cls.store_imm_ind(64), 1, False),
        }

    @staticmethod
    def store_imm_ind(bit_size: int) -> Callable[[Any, PyAssembler], None]:
        size_map = {8: Size.U8, 16: Size.U16, 32: Size.U32, 64: Size.U64}

        def impl(self: "InstructionsWArgs1Reg2Imm", asm: PyAssembler):
            # Prepare immediate value in RDX (scratch)
            asm.mov_imm64(Reg.rdx, int(self.vy % (2 ** bit_size)))

            # Compute effective memory address: mem_base (r14) + registers[ra] + vx
            # Use R15 as scratch if available to keep RDX for value (avoid clobbering guest regs).
            asm.mov(RegSize.R64, Reg.r15, r_map[self.ra])        # r15 = guest_reg[ra]
            if self.vx != 0:
                asm.add_imm64(Reg.r15, int(self.vx))

            mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r14, offset=0)
            # Using BaseOffset with runtime offset requires that *offset* be encoded at assemble-time.
            # Instead we treat r14 + r15 as [r14 + r15*1]. If the high-level MemOp API does not expose
            # a base+index encoding, we fallback to manual *store_reg_indexed* helper available in PyAssembler.
            try:
                from tsrkit_asm import StoreIndexedKind  # type: ignore
                asm.store_indexed(size_map[bit_size], kind=StoreIndexedKind.BaseIndex, base=Reg.r14, index=Reg.r15, reg=Reg.rdx)
            except ImportError:
                # Fallback: move address into RSI and use explicit mov instruction via PyAssembler helpers
                asm.lea(RegSize.R64, Reg.rsi, MemOp.BaseIndex(seg=None, size=RegSize.R64, base=Reg.r14, index=Reg.r15, scale=1))
                asm.store_reg_ptr(size_map[bit_size], ptr_reg=Reg.rsi, reg=Reg.rdx)
        return impl 
