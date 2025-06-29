from typing import Any, Callable, Dict, TYPE_CHECKING

from ..instruction_table import InstructionTable
from ..opcode import OpCode
from ...vm_context import r_map

from tsrkit_asm import RegSize


class InstructionsWArgs2Reg(InstructionTable):
    def rd(self) -> int:
        return min(12, self.program.zeta[self.counter + 1] % 16)

    @property
    def ra(self) -> int:
        return min(12, self.program.zeta[self.counter + 1] // 16)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            100: OpCode("move_reg", cls.move_reg, 1, False),
       }

    def move_reg(self, asm):  # noqa: D401
        """rd = ra"""
        asm.mov(size=RegSize.R64, a=r_map[self.rd], b=r_map[self.ra]) 
