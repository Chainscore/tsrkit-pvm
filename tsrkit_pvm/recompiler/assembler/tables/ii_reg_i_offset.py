from typing import Any, Callable, Dict, TYPE_CHECKING

from tsrkit_pvm.common.utils import z
from tsrkit_asm import Operands, Condition, RegMem, Size
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program

from ...vm_context import r_map


class InstructionsWArgs2Reg1Offset(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index


    def get_props(self):
        ra = min(12, int(self.program.zeta[self.counter + 1]) % 16)
        rb = min(12, int(self.program.zeta[self.counter + 1]) // 16)
        lx = min(4, max(0, self.skip_index - 1))
        start = self.counter + 2
        end = start + lx
        vx = self.counter + z(
            int.from_bytes(self.program.zeta[start:end], "little"), lx
        )
        return (ra, rb, lx, vx)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            170: OpCode(
                name="branch_eq", fn=cls.branch_eq, gas=1, is_terminating=False
            ),
            171: OpCode(
                name="branch_ne", fn=cls.branch_ne, gas=1, is_terminating=False
            ),
            172: OpCode(
                name="branch_lt_u", fn=cls.branch_lt_u, gas=1, is_terminating=False
            ),
            173: OpCode(
                name="branch_lt_s", fn=cls.branch_lt_s, gas=1, is_terminating=False
            ),
            174: OpCode(
                name="branch_ge_u", fn=cls.branch_ge_u, gas=1, is_terminating=False
            ),
            175: OpCode(
                name="branch_ge_s", fn=cls.branch_ge_s, gas=1, is_terminating=False
            ),
        }

    def branch_eq(self, asm, ra: int, rb: int, lx: int, vx: int):
        """Compare registers and branch if equal"""
        asm.cmp(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=r_map[rb]
            )
        )

        # Get the target address and find the corresponding label
        target_addr = vx
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.Equal, target_label)  # je target_label
        else:
            # Branch target not found - fall through (no jump)
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_ne(self, asm, ra: int, rb: int, lx: int, vx: int):
        """Compare registers and branch if not equal"""
        asm.cmp(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=r_map[rb]
            )
        )

        # Get the target address and find the corresponding label
        target_addr = vx
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.NotEqual, target_label)  # jne target_label
        else:
            # Branch target not found - fall through (no jump)
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_lt_u(self, asm, ra: int, rb: int, lx: int, vx: int):
        """Compare registers and branch if ra < rb (unsigned)"""
        asm.cmp(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=r_map[rb]
            )
        )

        # Get the target address and find the corresponding label
        target_addr = vx
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(
                Condition.Below, target_label
            )  # jb target_label (unsigned less than)
        else:
            # Branch target not found - fall through (no jump)
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_lt_s(self, asm, ra: int, rb: int, lx: int, vx: int):
        """Compare registers and branch if ra < rb (signed)"""
        asm.cmp(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=r_map[rb]
            )
        )

        # Get the target address and find the corresponding label
        target_addr = vx
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(
                Condition.Less, target_label
            )  # jl target_label (signed less than)
        else:
            # Branch target not found - fall through (no jump)
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_ge_u(self, asm, ra: int, rb: int, lx: int, vx: int):
        """Compare registers and branch if ra >= rb (unsigned)"""
        asm.cmp(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=r_map[rb]
            )
        )

        # Get the target address and find the corresponding label
        target_addr = vx
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(
                Condition.AboveOrEqual, target_label
            )  # jae target_label (unsigned greater or equal)
        else:
            # Branch target not found - fall through (no jump)
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_ge_s(self, asm, ra: int, rb: int, lx: int, vx: int):
        """Compare registers and branch if ra >= rb (signed)"""
        asm.cmp(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=r_map[rb]
            )
        )

        # Get the target address and find the corresponding label
        target_addr = vx
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(
                Condition.GreaterOrEqual, target_label
            )  # jge target_label (signed greater or equal)
        else:
            # Branch target not found - fall through (no jump)
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )
