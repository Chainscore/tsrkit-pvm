from typing import Dict

from ..instruction_table import InstructionTable
from ..opcode import OpCode


class InstructionsWoArgs(InstructionTable):
    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            0: OpCode(name="trap", fn=cls.trap, gas=1, is_terminating=True),
        }

    def trap(self, asm):
        """Generate x86 code for PVM trap instruction"""
        # Terminate execution safely
        asm.ret()  # return to caller instead of triggering UD2 (SIGILL)
