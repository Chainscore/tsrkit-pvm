from typing import Dict, TYPE_CHECKING

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program

from ...vm_context import r_map


class InstructionsWArgs1Imm1EwImm(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index


    def get_props(self):
        ra = min(12, self.program.zeta[self.counter + 1] % 16)
        vx = int.from_bytes(
            bytes(self.program.zeta[self.counter + 2 : self.counter + 10]), "little"
        )
        return (ra, vx)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            20: OpCode(
                name="load_imm_64", fn=cls.load_imm_64, gas=1, is_terminating=False
            )
        }

    def load_imm_64(self, asm, ra: int, vx: int):
        # Load 64-bit immediate value into register
        asm.mov_imm64(r_map[ra], vx)  # mov ra, vx (64-bit)
