from typing import Dict

from tsrkit_pvm.common.utils import z

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode


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
            40: OpCode(name="jump", fn=cls.jump, gas=1, is_terminating=False),
        }

    def jump(self, asm):
        """Jump to vx"""
        # asm.ud2()
        target_addr = self.vx
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jmp_label32(target_label)
        else:
            # For now, return from function if target not found
            # This handles cases where the jump target is outside the current compilation unit
            print(f"Warning: Jump target {target_addr} not found in labels, returning")
            asm.ret()
