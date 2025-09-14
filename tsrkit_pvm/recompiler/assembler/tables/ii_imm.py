from typing import Any, Callable, Dict, TYPE_CHECKING
from tsrkit_asm import Reg, MemOp, PyAssembler

from tsrkit_pvm.common.utils import z
from ...vm_context import r_map, TEMP_REG
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program


class InstructionsWArgs2Imm(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index


    def get_props(self):
        lx = min(4, self.program.zeta[self.counter + 1])
        ly = min(4, max(0, self.skip_index - int(lx) - 1))
        
        start = self.counter + 2
        end = start + lx
        vx = int.from_bytes(self.program.zeta[start:end], "little", signed=False)
        
        start = self.counter + 2 + lx
        end = start + ly
        vy = int.from_bytes(self.program.zeta[start:end], "little", signed=False)
        
        return (lx, ly, vx, vy)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            30: OpCode("store_imm_u8", cls.store_imm(8), 1, False),
            31: OpCode("store_imm_u16", cls.store_imm(16), 1, False),
            32: OpCode("store_imm_u32", cls.store_imm(32), 1, False),
            33: OpCode("store_imm_u64", cls.store_imm(64), 1, False),
        }

    @staticmethod
    def store_imm(bit_size: int) -> Callable[[Any, "PyAssembler", int, int, int, int], None]:
        from tsrkit_asm import Size, RegSize

        size_map = {8: Size.U8, 16: Size.U16, 32: Size.U32, 64: Size.U64}

        def impl(self, asm, lx: int, ly: int, vx: int, vy: int):
            imm_val = int(vy % (2**bit_size))
            asm.mov_imm64(TEMP_REG, imm_val)

            mem = MemOp.BaseOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,  # R15 holds memory base pointer
                offset=z(vx, 8),
            )
            asm.store(size_map[bit_size], mem=mem, reg=TEMP_REG)

        return impl
