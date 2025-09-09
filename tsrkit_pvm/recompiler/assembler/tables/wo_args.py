from typing import Dict

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode


class InstructionsWoArgs(InstructionTable):
    def get_props(self):
        return ()
    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            0: OpCode(name="trap", fn=cls.trap, gas=1, is_terminating=True),
            1: OpCode(
                name="fallthrough", fn=cls.fallthrough, gas=1, is_terminating=True
            ),
        }

    def trap(self, asm):
        """Generate x86 code for PVM trap instruction"""
        # Terminate execution safely
        asm.ret()

    def fallthrough(self, asm):
        """Generate x86 code for PVM fallthrough instruction"""
        # Fallthrough indicates normal termination, return to caller
        asm.nop()
