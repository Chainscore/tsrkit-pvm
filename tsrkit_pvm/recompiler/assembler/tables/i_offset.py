from typing import Dict

from tsrkit_pvm.interpreter.utils import z

from ..instruction_table import InstructionTable
from ..opcode import OpCode


class WArgsOneOffset(InstructionTable):
    @property
    def lx(self) -> int:
        return min(4, self.skip_index)
    
    @property
    def vx(self) -> int:
        start = self.counter + 1
        end = start + self.lx
        return int(self.counter) + z(
            int.from_bytes(
                self.program.zeta[start:end],
                "little"
            ),
            self.lx
        )
    
    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            40: OpCode(name="jump", fn=cls.jump, gas=1, is_terminating=False),
        }
    
    def jump(self, asm):
        """Generate x86 code for PVM jump instruction"""
        # Get the target address and find the corresponding label
        target_addr = self.vx
        if hasattr(asm, 'labels') and target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jmp_label32(target_label)
        else:
            # Fallback if label not found
            asm.ud2()  # This shouldn't happen in a well-formed program

