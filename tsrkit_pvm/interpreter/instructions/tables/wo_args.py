from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program
from ...memory import Memory
from ....common.status import CONTINUE, PANIC, PvmError
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn

class InstructionsWoArgs(InstructionTable):
    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self) -> list[int]:
        return []
    
    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            0: OpCode(name="trap", fn=cls.trap, gas=1, is_terminating=True),
            1: OpCode(
                name="fallthrough", fn=cls.fallthrough, gas=1, is_terminating=True
            ),
        }

    def trap(self, registers: list[int], memory: Memory) -> OpReturn:
        """
        OPC0: Trap the execution.
        """
        raise PvmError(PANIC)

    def fallthrough(self, registers: list[int], memory: Memory) -> OpReturn:
        """
        OPC1: Fall through to the next instruction.
        """
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory
