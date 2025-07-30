from typing import Dict

from ..instruction_table import InstructionTable
from ..opcode import OpCode


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
        """Emit return for unsupported host call.

        TODO: Implement this properly
        """
        print(f"Warning: ecalli instruction not implemented, returning")
        asm.ret()
