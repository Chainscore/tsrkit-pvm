from math import floor
from typing import Any, Callable, Dict

from tsrkit_pvm.interpreter.utils import chi

from ..instruction_table import InstructionTable
from ..opcode import OpCode
from ...vm_context import r_map

class InstructionsWArgs1Reg1Imm(InstructionTable):
    @property
    def ra(self) -> int:
        return min(12, int(self.program.zeta[self.counter + 1]) % 16)

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
            51: OpCode(name="load_imm", fn=cls.load_imm, gas=1, is_terminating=False),
        }

            
    def load_imm(self, asm):
        """Generate x86 code for PVM load_imm instruction"""
        # Load immediate value into register
        asm.mov_imm32(r_map[self.ra], self.vx & 0xFFFFFFFF)  # mov ra, vx (32-bit)
    
