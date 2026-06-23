from typing import Any, TYPE_CHECKING, Callable, Dict

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program

from ...memory import Memory
from ....common.status import CONTINUE
from ....common.utils import b, b_inv, chi, compare, compare_bits_vectorized, z, z_inv, clamp_12
from ....core.instruction_table import InstructionTable
from ....core.opcode import ExecutionUnits, OpCode, OpReturn
from ....gas.profiles import ALU, DIV_UNITS, LOAD_UNITS, MUL_UNITS, NO_UNITS, STORE_UNITS, profile

class InstructionsWArgs2Reg(InstructionTable):
    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    def get_props(self) -> list[int]:
        # Slice zeta once for better performance with large arrays
        zeta_slice = self.program.zeta[self.counter + 1:self.counter + 2]
        
        # Cache the byte value and use bit operations for faster parsing
        byte_val = zeta_slice[0]  # equivalent to self.program.zeta[self.counter + 1]
        rd = clamp_12(byte_val & 0x0F)  # Lower 4 bits (equivalent to % 16)
        ra = clamp_12(byte_val >> 4)    # Upper 4 bits (equivalent to // 16)
        return [rd, ra]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            100: OpCode(name="move_reg", fn=cls.move_reg, is_terminating=False, gas_profile=profile(0, 1, NO_UNITS)),
            101: OpCode(
                name="count_set_bits_64",
                fn=cls.count_set_bits(64),
                is_terminating=False,
                gas_profile=profile(1, 1, ALU),
            ),
            102: OpCode(
                name="count_set_bits_32",
                fn=cls.count_set_bits(32),
                is_terminating=False,
                gas_profile=profile(1, 1, ALU),
            ),
            103: OpCode(
                name="leading_zero_bits_64",
                fn=cls.leading_zero_bits(64),
                is_terminating=False,
                gas_profile=profile(1, 1, ALU),
            ),
            104: OpCode(
                name="leading_zero_bits_32",
                fn=cls.leading_zero_bits(32),
                is_terminating=False,
                gas_profile=profile(1, 1, ALU),
            ),
            105: OpCode(
                name="trailing_zero_bits_64",
                fn=cls.trailing_zero_bits(64),
                is_terminating=False,
                gas_profile=profile(2, 1, ExecutionUnits(2, 0, 0, 0, 0)),
            ),
            106: OpCode(
                name="trailing_zero_bits_32",
                fn=cls.trailing_zero_bits(32),
                is_terminating=False,
                gas_profile=profile(2, 1, ExecutionUnits(2, 0, 0, 0, 0)),
            ),
            107: OpCode(
                name="sign_extend_8", fn=cls.sign_extend(8), is_terminating=False,
                gas_profile=profile(1, 1, ALU)
            ),
            108: OpCode(
                name="sign_extend_16",
                fn=cls.sign_extend(16),
                is_terminating=False,
                gas_profile=profile(1, 1, ALU),
            ),
            109: OpCode(
                name="zero_extend_16",
                fn=cls.zero_extend_16,
                is_terminating=False,
                gas_profile=profile(1, 1, ALU),
            ),
            110: OpCode(
                name="reverse_bytes", fn=cls.reverse_bytes, is_terminating=False,
                gas_profile=profile(1, ("P", 1, 2), ALU)
            ),
        }

    def move_reg(self, registers: list[int], memory: Memory, rd: int, ra: int) -> OpReturn:
        registers[rd] = registers[ra]
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    @staticmethod
    def count_set_bits(bitsize: int) -> Callable[..., OpReturn]:
        def count_set_bits_impl(self: "InstructionsWArgs2Reg", registers: list[int], memory: Memory, rd: int, ra: int) -> OpReturn:
            registers[rd] = sum(
                b(int(registers[ra]) % 2**bitsize, bitsize // 8)[:bitsize]
            )
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return count_set_bits_impl

    @staticmethod
    def leading_zero_bits(bitsize: int) -> Callable[..., OpReturn]:
        def leading_zero_bits_impl(self: "InstructionsWArgs2Reg", registers: list[int], memory: Memory, rd: int, ra: int) -> OpReturn:
            try:
                leading_zeroes = b(
                    int(registers[ra]) % 2**bitsize, bitsize // 8
                )[::-1].index(True)
            except ValueError:
                leading_zeroes = bitsize
            registers[rd] = leading_zeroes
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return leading_zero_bits_impl

    @staticmethod
    def trailing_zero_bits(bitsize: int) -> Callable[..., OpReturn]:
        def trailing_zero_impl(self: "InstructionsWArgs2Reg", registers: list[int], memory: Memory, rd: int, ra: int) -> OpReturn:
            try:
                trailing_zeroes = b(
                    registers[ra] % 2**bitsize, bitsize // 8
                ).index(True)
            except ValueError:
                trailing_zeroes = bitsize
            registers[rd] = trailing_zeroes
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return trailing_zero_impl

    @staticmethod
    def sign_extend(bitsize: int) -> Callable[..., OpReturn]:
        def sign_extend_impl(self: "InstructionsWArgs2Reg", registers: list[int], memory: Memory, rd: int, ra: int) -> OpReturn:
            registers[rd] = z_inv(
                z(registers[ra] % 2**bitsize, bitsize // 8), 8
            )
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return sign_extend_impl

    def zero_extend_16(self, registers: list[int], memory: Memory, rd: int, ra: int) -> OpReturn:
        registers[rd] = int(registers[ra]) % 2**16
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def reverse_bytes(self, registers: list[int], memory: Memory, rd: int, ra: int) -> OpReturn:
        registers[rd] = int.from_bytes(
            registers[ra].to_bytes(8, "little")[::-1], "little"
        )
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory
