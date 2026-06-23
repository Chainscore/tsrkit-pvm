from typing import Dict, TYPE_CHECKING

from tsrkit_pvm.common.utils import z

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program


class WArgsOneOffset(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self):
        lx = min(4, self.skip_index)
        start = self.counter + 1
        end = start + lx
        vx = int(self.counter) + z(
            int.from_bytes(self.program.zeta[start:end], "little"), lx
        )
        return (lx, vx)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            40: OpCode(name="jump", fn=cls.jump, is_terminating=True),
        }

    def jump(self, asm, lx: int, vx: int):
        """Jump to vx"""
        # asm.ud2()
        target_addr = vx
        if target_addr == self.counter:
            return
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jmp_label32(target_label)
        else:
            asm.panic()
