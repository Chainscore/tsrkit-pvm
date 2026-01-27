from math import floor
from typing import Dict, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program

from ...memory import Memory
from ....common.utils import chi, compare, z, clamp_12, clamp_4, clamp_4_max0
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn

class InstructionsWArgs2Reg2Imm(InstructionTable):
    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self) -> list[int]:
        # Slice zeta once for better performance with large arrays
        zeta_slice = self.program.zeta[self.counter + 1:self.counter + 10]
        
        # Cache byte values and use bit operations for faster parsing
        byte_val1 = zeta_slice[0]  # equivalent to self.program.zeta[self.counter + 1]
        ra = clamp_12(byte_val1 & 0x0F)  # Lower 4 bits (equivalent to % 16)
        rb = clamp_12(byte_val1 >> 4)    # Upper 4 bits (equivalent to // 16)
        
        byte_val2 = int(zeta_slice[1])  # equivalent to self.program.zeta[self.counter + 2]
        lx = clamp_4(byte_val2 & 0x07)   # Lower 3 bits (equivalent to % 8)
        ly = clamp_4_max0(int(self.skip_index) - lx - 2)
        
        # Use sliced array for immediate values
        if lx > 0:
            imm1_slice = zeta_slice[2:2+lx]
            vx = chi(int.from_bytes(imm1_slice, "little"), lx)
        else:
            vx = 0
        
        if ly > 0:
            imm2_slice = zeta_slice[2+lx:2+lx+ly]
            vy = chi(int.from_bytes(imm2_slice, "little"), ly)
        else:
            vy = 0
        
        return [ra, rb, lx, ly, vx, vy]

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

    def load_imm_jump_ind(self, registers: list[int], memory: Memory, ra: int, rb: int, lx: int, ly: int, vx: int, vy: int) -> OpReturn:
        wb = registers[rb]
        registers[ra] = vx
        status, counter = self.program.djump(self.counter, floor(wb + vy) % 2**32) 
        return status, counter, registers, memory
