from typing import Dict

from ...memory import Memory
from ....common.status import CONTINUE
from ....common.utils import clamp_4, z
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn


class WArgsOneOffset(InstructionTable):
    def get_props(self):
        lx = clamp_4(self.skip_index)
        start = self.counter + 1
        end = start + lx
        vx = int(self.counter) + z(
            int.from_bytes(self.program.zeta[start:end], "little"), lx
        )
        return (lx, vx)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            40: OpCode(name="jump", fn=cls.jump, gas=1, is_terminating=True),
        }

    def jump(self, registers: list, memory: Memory, lx: int, vx: int) -> OpReturn:
        status, counter = self.program.branch(self.counter, vx, True)
        if status == CONTINUE and counter != self.counter:
            return status, counter, registers, memory
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory
