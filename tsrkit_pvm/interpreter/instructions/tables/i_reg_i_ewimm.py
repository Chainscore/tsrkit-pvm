from typing import Dict

from ...memory import Memory
from ....common.status import CONTINUE
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn
from ....common.utils import clamp_12


class InstructionsWArgs1Imm1EwImm(InstructionTable):
    def get_props(self):
        zeta_arr = self.program.zeta[self.counter + 1: self.counter + 10]
        ra = clamp_12(zeta_arr[0] % 16)
        vx = int.from_bytes(
            bytes(zeta_arr[1:9]), "little"
        )
        return (ra, vx)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            20: OpCode(
                name="load_imm_64", fn=cls.load_imm_64, gas=1, is_terminating=False
            )
        }

    def load_imm_64(self, registers: list, memory: Memory, ra: int, vx: int) -> OpReturn:
        """
        OPC20: Load a 64-bit immediate value into a register.
        """
        registers[ra] = vx
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory
