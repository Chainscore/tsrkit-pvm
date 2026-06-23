from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program
from ...memory import Memory
from ....common.status import CONTINUE, PANIC, PvmError
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn
from ....gas.profiles import ALU, DIV_UNITS, LOAD_UNITS, MUL_UNITS, NO_UNITS, STORE_UNITS, profile

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
            0: OpCode(name="trap", fn=cls.trap, is_terminating=True, gas_profile=profile(2, 1, NO_UNITS)),
            1: OpCode(
                name="fallthrough", fn=cls.fallthrough, is_terminating=True,
                gas_profile=profile(2, 1, NO_UNITS)
            ),
            2: OpCode(name="unlikely", fn=cls.unlikely, is_terminating=False, gas_profile=profile(40, 1, NO_UNITS)),
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

    def unlikely(self, registers: list[int], memory: Memory) -> OpReturn:
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory
