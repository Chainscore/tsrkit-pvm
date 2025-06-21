from typing import Dict

from ...memory import Memory
from ...status import HOST
from ...utils import chi
from ..instruction_table import InstructionTable
from ..opcode import OpCode, OpReturn


class InstructionsWArgs1Imm(InstructionTable):
    @property
    def lx(self) -> int:
        return min(4, self.skip_index)

    @property
    def vx(self) -> int:
        start = self.counter + 1
        end = start + self.lx
        return chi(
            int.from_bytes(
                self.program.zeta[start:end],
                "little"
            ),
            self.lx,
        )

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            10: OpCode(name="ecalli", fn=cls.ecalli, gas=1, is_terminating=False),
        }

    def ecalli(
        self, registers: list, memory: Memory
    ) -> OpReturn:
        """
        OPC10: Ecalli.
        """
        return HOST(self.vx), self.counter + self.skip_index + 1, registers, memory
