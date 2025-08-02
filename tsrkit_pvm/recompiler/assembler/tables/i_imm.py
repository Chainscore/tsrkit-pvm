from typing import Dict

from tsrkit_asm import Reg

from tsrkit_pvm.recompiler.assembler.utils import pop_all_regs, save_all_regs

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode


class InstructionsWArgs1Imm(InstructionTable):
    @property
    def lx(self) -> int:
        return min(4, self.skip_index)

    @property
    def vx(self) -> int:
        start = self.counter + 1
        end = start + self.lx
        return int.from_bytes(self.program.zeta[start:end], "little", signed=False)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            10: OpCode(name="ecalli", fn=cls.ecalli, gas=1, is_terminating=True),
        }

    def ecalli(self, asm):  # noqa: D401
        """Host call invocation"""
        PVM_SYS_CALL_OFFSET = 1000
        # Save all regs before exiting
        save_all_regs(asm)
        pop_all_regs(asm)  # This is safe to do so, not doing this also works
        # Load rax in rcx
        asm.mov_imm64(Reg.rax, PVM_SYS_CALL_OFFSET + self.vx)
        asm.syscall()
