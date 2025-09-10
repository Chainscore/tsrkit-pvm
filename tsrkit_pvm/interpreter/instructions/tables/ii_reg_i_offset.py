from typing import Any, Callable, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program

from ...memory import Memory
from ....common.status import CONTINUE
from ....common.utils import b, b_inv, chi, compare, z, z_inv, clamp_12, clamp_4, clamp_4_max0
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn


class InstructionsWArgs2Reg1Offset(InstructionTable):
    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self) -> List[int]:
        # Slice zeta once for better performance with large arrays
        zeta_slice = self.program.zeta[self.counter + 1:self.counter + 7]
        
        # Cache the byte value and use bit operations for faster parsing
        byte_val = int(zeta_slice[0])  # equivalent to self.program.zeta[self.counter + 1]
        ra = clamp_12(byte_val & 0x0F)  # Lower 4 bits (equivalent to % 16)
        rb = clamp_12(byte_val >> 4)    # Upper 4 bits (equivalent to // 16)
        lx = clamp_4_max0(self.skip_index - 1)
        
        # Use sliced array for offset value
        if lx > 0:
            offset_slice = zeta_slice[1:1+lx]
            vx = int(self.counter) + z(int.from_bytes(offset_slice, "little"), lx)
        else:
            vx = int(self.counter)
        return [ra, rb, lx, vx]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            170: OpCode(
                name="branch_eq", fn=cls.branch("eq"), gas=1, is_terminating=True
            ),
            171: OpCode(
                name="branch_ne", fn=cls.branch("ne"), gas=1, is_terminating=True
            ),
            172: OpCode(
                name="branch_lt_u", fn=cls.branch("lt"), gas=1, is_terminating=True
            ),
            173: OpCode(
                name="branch_lt_s",
                fn=cls.branch("lt", True),
                gas=1,
                is_terminating=True,
            ),
            174: OpCode(
                name="branch_ge_u", fn=cls.branch("ge"), gas=1, is_terminating=True
            ),
            175: OpCode(
                name="branch_ge_s",
                fn=cls.branch("ge", True),
                gas=1,
                is_terminating=True,
            ),
        }

    @staticmethod
    def branch(op: str, signed: bool = False) -> Callable[["InstructionsWArgs2Reg1Offset", list[int], Memory, int, int, int, int], OpReturn]:
        def branch_impl(self: "InstructionsWArgs2Reg1Offset", registers: list[int], memory: Memory, ra: int, rb: int, lx: int, vx: int) -> OpReturn:

            a = z(registers[ra], 8) if signed else registers[ra]
            b = z(registers[rb], 8) if signed else registers[rb]
            status, counter = self.program.branch(
                self.counter, vx, compare(a, b, op)
            )
            if status == CONTINUE and counter != self.counter:
                return status, counter, registers, memory
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return branch_impl
