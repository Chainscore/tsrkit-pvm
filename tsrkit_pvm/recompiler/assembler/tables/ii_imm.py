from typing import Any, Callable, Dict, TYPE_CHECKING

from tsrkit_asm import Reg, RegSize, Size, MemOp

from ..instruction_table import InstructionTable
from ..opcode import OpCode

from tsrkit_asm import PyAssembler


class InstructionsWArgs2Imm(InstructionTable):
    @property
    def lx(self) -> int:
        return min(4, self.program.zeta[self.counter + 1])

    @property
    def ly(self) -> int:
        return min(4, max(0, self.skip_index - int(self.lx) - 1))

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
            30: OpCode("store_imm_u8", cls.store_imm(8), 1, False),
            31: OpCode("store_imm_u16", cls.store_imm(16), 1, False),
            32: OpCode("store_imm_u32", cls.store_imm(32), 1, False),
            33: OpCode("store_imm_u64", cls.store_imm(64), 1, False),
        }

    @staticmethod
    def store_imm(bit_size: int) -> Callable[[Any, "PyAssembler"], None]:
        from tsrkit_asm import PyAssembler  # local import to avoid heavy import for type checking
        from tsrkit_asm import Size, RegSize

        size_map = {8: Size.U8, 16: Size.U16, 32: Size.U32, 64: Size.U64}

        def impl(self: "InstructionsWArgs2Imm", asm: PyAssembler):  # noqa: N802
            # Use RDX as a scratch register (not part of guest mapping)
            imm_val = int(self.vy % (2 ** bit_size))
            asm.mov_imm64(Reg.rdx, imm_val)

            mem = MemOp.BaseOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r14,  # R14 holds memory base pointer
                offset=int(self.vx),
            )
            asm.store(size_map[bit_size], mem=mem, reg=Reg.rdx)
        return impl 
