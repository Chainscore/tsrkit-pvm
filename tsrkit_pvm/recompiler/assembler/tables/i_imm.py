from typing import Dict, TYPE_CHECKING

from tsrkit_asm import Reg

from tsrkit_pvm.recompiler.assembler.utils import pop_all_regs, save_all_regs

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program


class InstructionsWArgs1Imm(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self):
        lx = min(4, self.skip_index)
        start = self.counter + 1
        end = start + lx
        vx = int.from_bytes(self.program.zeta[start:end], "little", signed=False)
        return (lx, vx)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            10: OpCode(name="ecalli", fn=cls.ecalli, gas=1, is_terminating=False),
        }

    def ecalli(self, asm, lx: int, vx: int):  # noqa: D401
        """Host call invocation"""
        PVM_SYS_CALL_OFFSET = 1000
        # Save all regs before exiting
        save_all_regs(asm)
        # pop_all_regs(asm)  # This is safe to do so, not doing this also works
        # Load rax in rcx

        asm.mov_imm64(Reg.rax, PVM_SYS_CALL_OFFSET + vx)
        asm.syscall()
