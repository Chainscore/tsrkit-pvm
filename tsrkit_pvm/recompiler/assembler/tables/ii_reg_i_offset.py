from typing import Any, Callable, Dict

from tsrkit_pvm.interpreter.utils import z

from ..instruction_table import InstructionTable
from ..opcode import OpCode
from ...vm_context import r_map


class InstructionsWArgs2Reg1Offset(InstructionTable):
    @property
    def ra(self) -> int:
        return min(12, int(self.program.zeta[self.counter + 1]) % 16)

    @property
    def rb(self) -> int:
        return min(12, int(self.program.zeta[self.counter + 1]) // 16)
    
    @property
    def lx(self) -> int:
        return min(4, max(0, self.skip_index - 1))
    
    @property
    def vx(self) -> int:
        start = self.counter + 2
        end = start + self.lx
        return self.counter + z(
            int.from_bytes(
                self.program.zeta[start:end],
                "little"
            ),
            self.lx
        )

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            171: OpCode(name="branch_ne", fn=cls.branch_ne, gas=1, is_terminating=False),
        }

    def branch_ne(self, asm):
        """Generate x86 code for PVM branch_ne instruction"""
        # Compare registers and branch if not equal
        asm.cmp(64, r_map[self.ra], r_map[self.rb])  # cmp ra, rb
        
        # Get the target address and find the corresponding label
        target_addr = self.vx
        if hasattr(asm, 'labels') and target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jne_label32(target_label)  # jne target_label
        else:
            # Fallback if label not found
            asm.ud2()  # This shouldn't happen in a well-formed program
