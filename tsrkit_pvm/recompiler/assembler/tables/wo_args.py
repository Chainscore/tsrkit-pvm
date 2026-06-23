from typing import Dict, TYPE_CHECKING

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program


class InstructionsWoArgs(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self):
        return ()

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            0: OpCode(name="trap", fn=cls.trap, is_terminating=True),
            1: OpCode(
                name="fallthrough", fn=cls.fallthrough, is_terminating=True
            ),
            2: OpCode(name="unlikely", fn=cls.unlikely, is_terminating=False),
        }

    def trap(self, asm):
        """Generate x86 code for PVM trap instruction"""
        asm.panic()

    def fallthrough(self, asm):
        """Generate x86 code for PVM fallthrough instruction"""
        # Fallthrough indicates normal termination, return to caller
        asm.nop()

    def unlikely(self, asm):
        """Generate x86 code for PVM unlikely instruction."""
        asm.nop()
