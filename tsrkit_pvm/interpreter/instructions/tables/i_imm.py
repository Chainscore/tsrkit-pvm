from typing import Dict

from ...memory import Memory
from ....common.status import HOST
from ....common.utils import chi, clamp_4
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn


class InstructionsWArgs1Imm(InstructionTable):
    def get_props(self):
        lx = clamp_4(self.skip_index)
        start = self.counter + 1
        end = start + lx
        return (
            lx, 
            chi(
                int.from_bytes(self.program.zeta[start:end], "little"),
                lx,
            )
        )

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            10: OpCode(name="ecalli", fn=cls.ecalli, gas=1, is_terminating=False),
        }

    def ecalli(self, registers: list, memory: Memory, lx: int, vx: int) -> OpReturn:
        """
        OPC10: Ecalli.
        """
        return HOST(vx), self.counter + self.skip_index + 1, registers, memory
