from typing import Any, Callable, Dict

from tsrkit_pvm.interpreter.utils import chi
from tsrkit_asm import Operands, RegMem, ImmKind, Size, RegSize 
from ..instruction_table import InstructionTable
from ..opcode import OpCode
from ...vm_context import r_map


class InstructionsWArgs2Reg1Imm(InstructionTable):
    @property
    def ra(self) -> int:
        return min(12, self.program.zeta[self.counter + 1] % 16)

    @property
    def rb(self) -> int:
        return min(12, self.program.zeta[self.counter + 1] // 16)
    
    @property
    def lx(self) -> int:
        return min(4, max(0, self.skip_index - 1))
    
    @property
    def vx(self) -> int:
        start = self.counter + 2
        end = start + self.lx
        return chi(
            int.from_bytes(
                self.program.zeta[start:end],
                "little"
                ),
            self.lx
        )

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            149: OpCode(name="add_imm_64",          fn=cls.add_imm_64,             gas=1,         is_terminating=False),
       }

    def add_imm_64(self, asm):
        """ra = rb + vx"""
        
       # Load rb into ra 
        asm.mov(size=RegSize.R64, a=r_map[self.ra], b=r_map[self.rb])  
        # Add vx to rb 
        asm.add(Operands.RegMem_Imm(reg_mem=RegMem.Reg(r_map[self.ra]), imm=ImmKind.I64(self.vx)))
        
