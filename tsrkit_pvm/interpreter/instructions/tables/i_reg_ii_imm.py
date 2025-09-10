from typing import Any, Callable, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program

from ...memory import Memory
from ....common.status import CONTINUE
from ....common.utils import chi, compare, z, clamp_12, clamp_4, clamp_4_max0
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn


class InstructionsWArgs1Reg2Imm(InstructionTable):
    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self) -> list[int]:
        # Cache the byte value and use bit operations for faster parsing
        byte_val = self.program.zeta[self.counter + 1]
        ra = clamp_12(byte_val & 0x0F)           # Lower 4 bits (equivalent to % 16)
        lx = clamp_4((byte_val >> 4) & 0x07)     # Next 3 bits (equivalent to (// 16) % 8)
        ly = clamp_4_max0(self.skip_index - lx - 1)
        
        start = self.counter + 2
        end = start + lx
        vx = chi(int.from_bytes(self.program.zeta[start:end], "little"), lx)
        
        start = self.counter + 2 + lx
        end = start + ly
        vy = chi(int.from_bytes(self.program.zeta[start:end], "little"), ly)

        return [ra, lx, ly, vx, vy]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            70: OpCode(
                name="store_imm_ind_u8",
                fn=cls.store_imm_ind_u(8),
                gas=1,
                is_terminating=False,
            ),
            71: OpCode(
                name="store_imm_ind_u16",
                fn=cls.store_imm_ind_u(16),
                gas=1,
                is_terminating=False,
            ),
            72: OpCode(
                name="store_imm_ind_u32",
                fn=cls.store_imm_ind_u(32),
                gas=1,
                is_terminating=False,
            ),
            73: OpCode(
                name="store_imm_ind_u64",
                fn=cls.store_imm_ind_u(64),
                gas=1,
                is_terminating=False,
            ),
        }

    @staticmethod
    def store_imm_ind_u(bitsize: int) -> Callable[["InstructionsWArgs1Reg2Imm", list[int], Memory, int, int, int, int, int], OpReturn]:
        def store_u_impl(self: InstructionsWArgs1Reg2Imm, registers: list[int], memory: Memory, ra: int, lx: int, ly: int, vx: int, vy: int) -> OpReturn:
            memory.write(
                registers[ra] + vx,
                int(vy % (2**bitsize)).to_bytes(bitsize // 8, "little"),
            )
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return store_u_impl
