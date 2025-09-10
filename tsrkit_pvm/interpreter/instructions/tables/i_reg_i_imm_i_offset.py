from typing import Any, TYPE_CHECKING, Callable, Dict

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program

from ...memory import Memory
from ....common.status import CONTINUE
from ....common.utils import chi, compare, z, clamp_12, clamp_4, clamp_4_max0
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn

class InstructionsWArgs1Reg1Imm1Offset(InstructionTable):
    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self) -> list[int]:
        # Slice zeta once for better performance with large arrays
        zeta_slice = self.program.zeta[self.counter + 1:self.counter + 8]
        
        # Cache the byte value and use bit operations for faster parsing
        byte_val = int(zeta_slice[0])  # equivalent to self.program.zeta[self.counter + 1]
        ra = clamp_12(byte_val & 0x0F)           # Lower 4 bits (equivalent to % 16)
        lx = clamp_4((byte_val >> 4) & 0x07)     # Next 3 bits (equivalent to (// 16) % 8)
        ly = clamp_4_max0(int(self.skip_index) - lx - 1)
        
        # Use sliced array for immediate values
        if lx > 0:
            imm1_slice = zeta_slice[1:1+lx]
            vx = chi(int.from_bytes(imm1_slice, "little"), lx)
        else:
            vx = 0
        
        if ly > 0:
            imm2_slice = zeta_slice[1+lx:1+lx+ly]
            vy = int(self.counter) + z(int.from_bytes(imm2_slice, "little"), ly)
        else:
            vy = int(self.counter)
        
        return [ra, lx, ly, vx, vy]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            80: OpCode(
                name="load_imm_jump", fn=cls.load_imm_jump, gas=1, is_terminating=True
            ),
            81: OpCode(
                name="branch_eq_imm",
                fn=cls.branch_imm("eq"),
                gas=1,
                is_terminating=True,
            ),
            82: OpCode(
                name="branch_ne_imm",
                fn=cls.branch_imm("ne"),
                gas=1,
                is_terminating=True,
            ),
            83: OpCode(
                name="branch_lt_u_imm",
                fn=cls.branch_imm("lt"),
                gas=1,
                is_terminating=True,
            ),
            84: OpCode(
                name="branch_le_u_imm",
                fn=cls.branch_imm("le"),
                gas=1,
                is_terminating=True,
            ),
            85: OpCode(
                name="branch_ge_u_imm",
                fn=cls.branch_imm("ge"),
                gas=1,
                is_terminating=True,
            ),
            86: OpCode(
                name="branch_gt_u_imm",
                fn=cls.branch_imm("gt"),
                gas=1,
                is_terminating=True,
            ),
            87: OpCode(
                name="branch_lt_s_imm",
                fn=cls.branch_imm("lt", True),
                gas=1,
                is_terminating=True,
            ),
            88: OpCode(
                name="branch_le_s_imm",
                fn=cls.branch_imm("le", True),
                gas=1,
                is_terminating=True,
            ),
            89: OpCode(
                name="branch_ge_s_imm",
                fn=cls.branch_imm("ge", True),
                gas=1,
                is_terminating=True,
            ),
            90: OpCode(
                name="branch_gt_s_imm",
                fn=cls.branch_imm("gt", True),
                gas=1,
                is_terminating=True,
            ),
        }

    def load_imm_jump(self, registers: list[int], memory: Memory, ra: int, lx: int, ly: int, vx: int, vy: int) -> OpReturn:
        registers[ra] = vx
        status, counter = self.program.branch(self.counter, vy, True)
        if status == CONTINUE and counter != self.counter:
            return status, counter, registers, memory
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    @staticmethod
    def branch_imm(op: str, signed: bool = False) -> Callable[["InstructionsWArgs1Reg1Imm1Offset", list[int], Memory, int, int, int, int, int], OpReturn]:
        def branch_u_imm_impl(self: "InstructionsWArgs1Reg1Imm1Offset", registers: list[int], memory: Memory, ra: int, lx: int, ly: int, vx: int, vy: int) -> OpReturn:
            status, counter = self.program.branch(
                self.counter,
                vy,
                compare(
                    z(registers[ra], 8) if signed else registers[ra],
                    z(vx, 8) if signed else vx,
                    op,
                ),
            )
            if status == CONTINUE and counter != self.counter:
                return status, counter, registers, memory
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return branch_u_imm_impl
