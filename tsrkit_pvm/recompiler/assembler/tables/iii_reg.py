from typing import Any, Callable, Dict, TYPE_CHECKING
from ..instruction_table import InstructionTable
from ..opcode import OpCode
from ...vm_context import r_map
from tsrkit_asm import RegSize


class InstructionsWArgs3Reg(InstructionTable):
    @property
    def rd(self) -> int:
        return min(12, self.program.zeta[self.counter + 1] % 16)

    @property
    def ra(self) -> int:
        return min(12, (self.program.zeta[self.counter + 1] // 16) % 16)

    @property
    def rb(self) -> int:
        return min(12, self.program.zeta[self.counter + 2] % 16)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            200: OpCode("add_64", cls.add_64, 1, False),
       }

    def add_64(self, asm):
        """rd = ra + rb (64-bit)"""
        asm.mov(size=RegSize.R64, a=r_map[self.rd], b=r_map[self.ra])
        asm.add(size=RegSize.R64, a=r_map[self.rd], b=r_map[self.rb]) 
