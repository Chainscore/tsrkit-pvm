from typing import Dict

from ...memory import Memory
from ....common.status import CONTINUE
from ....common.utils import z
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn


class WArgsOneOffset(InstructionTable):
    @property
    def lx(self) -> int:
        return min(4, self.skip_index)

    @property
    def vx(self) -> int:
        start = self.counter + 1
        end = start + self.lx
        return int(self.counter) + z(
            int.from_bytes(self.program.zeta[start:end], "little"), self.lx
        )

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            40: OpCode(name="jump", fn=cls.jump, gas=1, is_terminating=True),
        }

    def jump(self, registers: list, memory: Memory) -> OpReturn:
        status, counter = self.program.branch(self.counter, self.vx, True)
        if status == CONTINUE and counter != self.counter:
            return status, counter, registers, memory
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory
