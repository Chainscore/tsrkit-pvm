from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program

from ...memory import Memory
from ....common.status import HOST
from ....common.utils import chi, clamp_4
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn

class InstructionsWArgs1Imm(InstructionTable):
    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self) -> list[int]:
        lx = clamp_4(self.skip_index)
        start = self.counter + 1
        end = start + lx
        return [
            lx,
            chi(
                int.from_bytes(self.program.zeta[start:end], "little"),
                lx,
            )
        ]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            10: OpCode(name="ecalli", fn=cls.ecalli, gas=1, is_terminating=False),
        }

    def ecalli(self, registers: list[int], memory: Memory, lx: int, vx: int) -> OpReturn:
        """
        OPC10: Ecalli.
        """
        return HOST(vx), self.counter + self.skip_index + 1, registers, memory
