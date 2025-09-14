from typing import Dict, TYPE_CHECKING
from tsrkit_pvm.common.utils import z
from tsrkit_asm import Operands, Condition, RegMem, ImmKind
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program

from ...vm_context import r_map


class InstructionsWArgs1Reg1Imm1Offset(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index


    def get_props(self):
        ra = min(12, int(self.program.zeta[self.counter + 1]) % 16)
        
        # Extract length encoding from register byte
        length_info = int(self.program.zeta[self.counter + 1]) // 16
        
        # Length of immediate value in bytes
        lx = length_info
        
        # Immediate value
        start = self.counter + 2
        end = start + lx
        vx = z(int.from_bytes(self.program.zeta[start:end], "little"), lx)
        
        # Length of offset value in bytes
        ly = self.skip_index - 1 - lx
        
        # Target address (current position + offset)
        start = self.counter + 2 + lx
        end = start + ly
        offset = z(int.from_bytes(self.program.zeta[start:end], "little"), ly)
        vy = self.counter + offset
        
        return (ra, length_info, lx, vx, ly, vy)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            80: OpCode(
                name="load_imm_jump", fn=cls.load_imm_jump, gas=1, is_terminating=False
            ),
            81: OpCode(
                name="branch_eq_imm", fn=cls.branch_eq_imm, gas=1, is_terminating=False
            ),
            82: OpCode(
                name="branch_ne_imm", fn=cls.branch_ne_imm, gas=1, is_terminating=False
            ),
            83: OpCode(
                name="branch_lt_u_imm",
                fn=cls.branch_lt_u_imm,
                gas=1,
                is_terminating=False,
            ),
            84: OpCode(
                name="branch_le_u_imm",
                fn=cls.branch_le_u_imm,
                gas=1,
                is_terminating=False,
            ),
            85: OpCode(
                name="branch_ge_u_imm",
                fn=cls.branch_ge_u_imm,
                gas=1,
                is_terminating=False,
            ),
            86: OpCode(
                name="branch_gt_u_imm",
                fn=cls.branch_gt_u_imm,
                gas=1,
                is_terminating=False,
            ),
            87: OpCode(
                name="branch_lt_s_imm",
                fn=cls.branch_lt_s_imm,
                gas=1,
                is_terminating=False,
            ),
            88: OpCode(
                name="branch_le_s_imm",
                fn=cls.branch_le_s_imm,
                gas=1,
                is_terminating=False,
            ),
            89: OpCode(
                name="branch_ge_s_imm",
                fn=cls.branch_ge_s_imm,
                gas=1,
                is_terminating=False,
            ),
            90: OpCode(
                name="branch_gt_s_imm",
                fn=cls.branch_gt_s_imm,
                gas=1,
                is_terminating=False,
            ),
        }

    def load_imm_jump(self, asm, ra, length_info, lx, vx, ly, vy):
        """Load immediate value into register and jump to target address"""
        # Load immediate value into register
        asm.mov_imm64(r_map[ra], vx)

        # Jump to target address
        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jmp_label32(target_label)
        else:
            # Fallback if label not found
            asm.ud2()  # This shouldn't happen in a well-formed program

    def branch_eq_imm(self, asm, ra, length_info, lx, vx, ly, vy):
        """Branch if register equals immediate value"""
        # Compare register to immediate value
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(vx)
            )
        )

        # Get the target address and find the corresponding label
        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.Equal, target_label)
        else:
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_ne_imm(self, asm, ra, length_info, lx, vx, ly, vy):
        """Branch if register not equals immediate value"""
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(vx)
            )
        )

        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.NotEqual, target_label)
        else:
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_lt_u_imm(self, asm, ra, length_info, lx, vx, ly, vy):
        """Branch if register less than immediate value (unsigned)"""
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(vx)
            )
        )

        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.Below, target_label)
        else:
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_lt_s_imm(self, asm, ra, length_info, lx, vx, ly, vy):
        """Branch if register less than immediate value (signed)"""
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(vx)
            )
        )

        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.Less, target_label)
        else:
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_ge_u_imm(self, asm, ra, length_info, lx, vx, ly, vy):
        """Branch if register greater than or equal to immediate value (unsigned)"""
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(vx)
            )
        )

        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.AboveOrEqual, target_label)
        else:
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_ge_s_imm(self, asm, ra, length_info, lx, vx, ly, vy):
        """Branch if register greater than or equal to immediate value (signed)"""
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(vx)
            )
        )

        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.GreaterOrEqual, target_label)
        else:
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_gt_u_imm(self, asm, ra, length_info, lx, vx, ly, vy):
        """Branch if register greater than immediate value (unsigned)"""
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(vx)
            )
        )

        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.Above, target_label)
        else:
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_gt_s_imm(self, asm, ra, length_info, lx, vx, ly, vy):
        """Branch if register greater than immediate value (signed)"""
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(vx)
            )
        )

        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.Greater, target_label)
        else:
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_le_u_imm(self, asm, ra, length_info, lx, vx, ly, vy):
        """Branch if register less than or equal to immediate value (unsigned)"""
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(vx)
            )
        )

        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.BelowOrEqual, target_label)
        else:
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )

    def branch_le_s_imm(self, asm, ra, length_info, lx, vx, ly, vy):
        """Branch if register less than or equal to immediate value (signed)"""
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(vx)
            )
        )

        target_addr = vy
        if target_addr in asm.labels:
            target_label = asm.labels[target_addr]
            asm.jcc_label32(Condition.LessOrEqual, target_label)
        else:
            print(
                f"Warning: Branch target {target_addr} not found in labels, falling through"
            )
