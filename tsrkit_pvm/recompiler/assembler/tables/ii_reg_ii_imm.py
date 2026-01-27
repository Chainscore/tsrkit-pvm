from typing import Any, Callable, Dict, TYPE_CHECKING
from math import floor

from tsrkit_pvm.common.utils import chi
from tsrkit_asm import (
    LoadKind,
    Reg,
    RegIndex,
    RegSize,
    MemOp,
    Operands,
    RegMem,
    ImmKind,
    Condition,
    Scale,
    Size,
)
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program

from ...vm_context import VMContext, r_map, TEMP_REG


class InstructionsWArgs2Reg2Imm(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index


    def get_props(self):
        ra = min(12, self.program.zeta[self.counter + 1] % 16)
        rb = min(12, int(self.program.zeta[self.counter + 1]) // 16)
        lx = min(4, int(self.program.zeta[self.counter + 2]) % 8)
        ly = min(4, max(0, int(self.skip_index) - lx - 2))
        
        start = self.counter + 3
        end = start + lx
        vx = chi(int.from_bytes(self.program.zeta[start:end], "little"), lx)
        
        start = self.counter + 3 + lx
        end = start + ly
        vy = chi(int.from_bytes(self.program.zeta[start:end], "little"), ly)
        
        return (ra, rb, lx, ly, vx, vy)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            180: OpCode(
                name="load_imm_jump_ind",
                fn=cls.load_imm_jump_ind,
                gas=1,
                is_terminating=True,
            ),
        }

    def load_imm_jump_ind(self, asm, ra, rb, lx, ly, vx, vy):
        """Load immediate into ra, then jump to address loaded from jump table[rb + vy]

        This implements: registers[ra] = vx; djump(counter, (registers[rb] + vy) % 2**32)
        """
        # Part 1: Load immediate vx into register ra
        # Part 2: Calculate the PVM address: rb + vy
        # Use rcx as temp register for address calculation

        if vy != 0:
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.add(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I64(vy)
                )
            )
        else:
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])

        asm.mov_imm64(r_map[ra], vx)
        # Ensure 32-bit wrap: rcx = rcx % 2**32
        asm.mov(size=RegSize.R32, a=TEMP_REG, b=TEMP_REG)

        # Part 3: Check if it's the halt value (2**32 - 2**16)
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I32(2**32 - 2**16)
            )
        )
        asm.jcc_label32(Condition.Equal, asm.halt_label)

        # Part 4: Validate PVM address (check alignment, bounds, etc.)
        # Check if pvm_address == 0 (invalid)
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U32, reg_mem=RegMem.Reg(TEMP_REG), reg=TEMP_REG
            )
        )
        asm.jcc_label32(Condition.Equal, asm.panic_label)

        # Check alignment: pvm_address % 2 == 0
        asm.test(Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I32(1)))
        asm.jcc_label32(Condition.NotEqual, asm.panic_label)

        # Calculate jump table index: (pvm_address / 2) - 1
        asm.shr_imm(RegSize.R64, RegMem.Reg(TEMP_REG), 1)  # rcx = pvm_address / 2
        asm.dec(Size.U64, RegMem.Reg(TEMP_REG))  # -= 1

        # Load jump_table_len
        # Check bounds: index >= jump_table_len
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I32(asm.jump_table_len)
            )
        )
        asm.jcc_label32(Condition.AboveOrEqual, asm.panic_label)

        # Jump to the machine code address
        asm.jmp(
            RegMem.Mem(
                MemOp.BaseIndexScaleOffset(
                    seg=None,
                    size=RegSize.R64,
                    base=Reg.r15,
                    index=RegIndex.rcx,
                    scale=Scale.x8,
                    offset=-VMContext.calculate_size(asm.jump_table_len),
                )
            )
        )
