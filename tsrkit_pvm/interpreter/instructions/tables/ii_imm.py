from typing import Any, TYPE_CHECKING, Callable, Dict

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program

from ...memory import Memory
from ....common.status import CONTINUE
from ....common.utils import chi, clamp_4, clamp_4_max0
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn

class InstructionsWArgs2Imm(InstructionTable):
    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self) -> list[int]:
        lx = clamp_4(self.program.zeta[self.counter + 1])
        ly = clamp_4_max0(self.skip_index - int(lx) - 1)
        
        start = self.counter + 2
        end = start + lx
        vx = chi(
            int.from_bytes(self.program.zeta[start:end], "little"),
            lx,
        )
        
        start = self.counter + 2 + lx
        end = start + ly
        vy = chi(
            int.from_bytes(self.program.zeta[start:end], "little"),
            ly,
        )

        return [lx, ly, vx, vy]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            30: OpCode(
                name="store_imm_u8", fn=cls.store_imm(8), gas=1, is_terminating=False
            ),
            31: OpCode(
                name="store_imm_u16", fn=cls.store_imm(16), gas=1, is_terminating=False
            ),
            32: OpCode(
                name="store_imm_u32", fn=cls.store_imm(32), gas=1, is_terminating=False
            ),
            33: OpCode(
                name="store_imm_u64", fn=cls.store_imm(64), gas=1, is_terminating=False
            ),
        }

    @staticmethod
    def store_imm(bit_size: int) -> Callable[..., OpReturn]:
        """Store an immediate value into memory. Implements the store_imm_u8, store_imm_u16, store_imm_u32, and store_imm_u64 instructions.

        Args:
            bit_size (int): The bit size of the immediate value to store. Could be 8 for storing u8, 16 for u16, etc.

        Returns:
            Callable[[Registers, Memory], Tuple[ExecutionStatus, Registers, Memory]]: The function to store the immediate value into memory.
        """

        def store_imm_impl(self: "InstructionsWArgs2Imm", registers: list[int], memory: Memory, lx: int, ly: int, vx: int, vy: int) -> OpReturn:
            memory.write(
                vx, int(vy % 2**bit_size).to_bytes(bit_size // 8, "little")
            )
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return store_imm_impl
