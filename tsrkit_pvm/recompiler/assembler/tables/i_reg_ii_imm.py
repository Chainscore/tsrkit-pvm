from typing import Any, Callable, Dict, TYPE_CHECKING

from tsrkit_pvm.common.utils import chi, z

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program

from ...vm_context import r_map, TEMP_REG, rindex_map

from tsrkit_asm import (
    ImmKind,
    Reg,
    RegSize,
    Size,
    MemOp,
    PyAssembler,
    Operands,
    RegMem,
    RegIndex,
    Scale,
)


class InstructionsWArgs1Reg2Imm(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self):
        ra = min(12, self.program.zeta[self.counter + 1] % 16)
        lx = min(4, (self.program.zeta[self.counter + 1] // 16) % 8)
        ly = min(4, max(0, int(self.skip_index) - lx - 1))
        
        start = self.counter + 2
        end = start + lx
        vx = chi(int.from_bytes(self.program.zeta[start:end], "little"), lx)
        
        start = self.counter + 2 + lx
        end = start + ly
        vy = chi(int.from_bytes(self.program.zeta[start:end], "little"), ly)
        
        return (ra, lx, ly, vx, vy)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            70: OpCode("store_imm_ind_u8", cls.store_imm_ind(Size.U8), 1, False),
            71: OpCode("store_imm_ind_u16", cls.store_imm_ind(Size.U16), 1, False),
            72: OpCode("store_imm_ind_u32", cls.store_imm_ind(Size.U32), 1, False),
            73: OpCode("store_imm_ind_u64", cls.store_imm_ind(Size.U64), 1, False),
        }

    @staticmethod
    def store_imm_ind(size: Size):
        def store_imm_ind(self, asm: PyAssembler, ra: int, lx: int, ly: int, vx: int, vy: int):
            """u<size>[ra + vx] = vy"""
            asm.mov_imm64(TEMP_REG, vy)
            # Store immediate value to calculated address
            asm.store(
                size,
                MemOp.BaseIndexScaleOffset(
                    seg=None,
                    size=RegSize.R64,
                    base=Reg.r15,
                    index=rindex_map[ra],
                    scale=Scale.x1,
                    offset=z(vx, 8),
                ),
                TEMP_REG,
            )

        return store_imm_ind
