from typing import Dict

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ...vm_context import r_map


class InstructionsWArgs1Imm1EwImm(InstructionTable):
    @property
    def ra(self) -> int:
        return min(12, self.program.zeta[self.counter + 1] % 16)

    @property
    def vx(self) -> int:
        value = int.from_bytes(
            bytes(self.program.zeta[self.counter + 2 : self.counter + 10]), "little"
        )
        return value

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            20: OpCode(
                name="load_imm_64", fn=cls.load_imm_64, gas=1, is_terminating=False
            )
        }

    def load_imm_64(self, asm):
        # Load 64-bit immediate value into register
        asm.mov_imm64(r_map[self.ra], self.vx)  # mov ra, vx (64-bit)
