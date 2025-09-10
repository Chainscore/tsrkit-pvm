from math import floor
from typing import Any, TYPE_CHECKING, Callable, Dict

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program

from ...memory import Memory
from ....common.status import CONTINUE
from ....common.utils import chi, clamp_12, clamp_4
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn

class InstructionsWArgs1Reg1Imm(InstructionTable):
    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self) -> list[int]:
        lx = clamp_4(max(0, self.skip_index - 1))
        zeta_arr = self.program.zeta[self.counter + 1: self.counter + 1 + 1 + lx]
        ra = clamp_12(zeta_arr[0] % 16)
        vx = chi(int.from_bytes(zeta_arr[1:9], "little"), lx)
        return [ra, lx, vx]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            50: OpCode(name="jump_ind", fn=cls.jump_ind, gas=1, is_terminating=True),
            51: OpCode(name="load_imm", fn=cls.load_imm, gas=1, is_terminating=False),
            52: OpCode(name="load_u8", fn=cls.load_u(8), gas=1, is_terminating=False),
            53: OpCode(name="load_i8", fn=cls.load_i(8), gas=1, is_terminating=False),
            54: OpCode(name="load_u16", fn=cls.load_u(16), gas=1, is_terminating=False),
            55: OpCode(name="load_i16", fn=cls.load_i(16), gas=1, is_terminating=False),
            56: OpCode(name="load_u32", fn=cls.load_u(32), gas=1, is_terminating=False),
            57: OpCode(name="load_i32", fn=cls.load_i(32), gas=1, is_terminating=False),
            58: OpCode(name="load_u64", fn=cls.load_u(64), gas=1, is_terminating=False),
            59: OpCode(name="store_u8", fn=cls.store_u(8), gas=1, is_terminating=False),
            60: OpCode(
                name="store_u16", fn=cls.store_u(16), gas=1, is_terminating=False
            ),
            61: OpCode(
                name="store_u32", fn=cls.store_u(32), gas=1, is_terminating=False
            ),
            62: OpCode(
                name="store_u64", fn=cls.store_u(64), gas=1, is_terminating=False
            ),
        }

    def jump_ind(self, registers: list[int], memory: Memory, ra: int, lx: int, vx: int) -> OpReturn:
        status, counter = self.program.djump( 
            self.counter, floor(int(registers[ra]) + vx) % 2**32
        )
        return status, counter, registers, memory

    def load_imm(self, registers: list[int], memory: Memory, ra: int, lx: int, vx: int) -> OpReturn:
        """
        OPC20: Load a 64-bit immediate value into a register.
        """
        registers[ra] = vx
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    @staticmethod
    def load_u(bitsize: int) -> Callable[..., OpReturn]:
        def load_u_impl(self: "InstructionsWArgs1Reg1Imm", registers: list[int], memory: Memory, ra: int, lx: int, vx: int) -> OpReturn:
            registers[ra] = int.from_bytes(
                memory.read(vx, bitsize // 8), "little"
            )
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return load_u_impl

    @staticmethod
    def store_u(bitsize: int) -> Callable[..., OpReturn]:
        def store_u_impl(self: "InstructionsWArgs1Reg1Imm", registers: list[int], memory: Memory, ra: int, lx: int, vx: int) -> OpReturn:
            memory.write(
                vx,
                int(registers[ra] % (2**bitsize)).to_bytes(bitsize // 8, "little"),
            )
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return store_u_impl

    @staticmethod
    def load_i(bitsize: int) -> Callable[..., OpReturn]:
        def load_i_impl(self: "InstructionsWArgs1Reg1Imm", registers: list[int], memory: Memory, ra: int, lx: int, vx: int) -> OpReturn:
            registers[ra] = chi(
                int.from_bytes(memory.read(vx, bitsize // 8), "little"),
                bitsize // 8,
            )
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return load_i_impl
