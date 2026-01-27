from decimal import Decimal
from math import trunc
from typing import Any, TYPE_CHECKING, Callable, Dict, List

if TYPE_CHECKING:
    from ....interpreter.program import INT_Program

from ...memory import Memory
from ....common.status import CONTINUE
from ....common.utils import b, b_inv, chi, compare, compare_bits_vectorized, smod, z, z_inv, clamp_12
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode, OpReturn


class InstructionsWArgs3Reg(InstructionTable):
    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index
        
    def get_props(self) -> List[int]:
        # Slice zeta once for better performance with large arrays  
        zeta_slice = self.program.zeta[self.counter + 1:self.counter + 3]
        
        # Cache the byte values and use bit operations for faster parsing
        byte_val = zeta_slice[0]  # equivalent to self.program.zeta[self.counter + 1]
        ra = clamp_12(byte_val & 0x0F)  # Lower 4 bits (equivalent to % 16)
        rb = clamp_12(byte_val >> 4)    # Upper 4 bits (equivalent to // 16)
        rd = clamp_12(zeta_slice[1])     # equivalent to self.program.zeta[self.counter + 2]
        return [ra, rb, rd]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            190: OpCode(name="add_32", fn=cls.add_32, gas=1, is_terminating=False),
            191: OpCode(name="sub_32", fn=cls.sub_32, gas=1, is_terminating=False),
            192: OpCode(name="mul_32", fn=cls.mul_32, gas=1, is_terminating=False),
            193: OpCode(name="div_u_32", fn=cls.div_u_32, gas=1, is_terminating=False),
            194: OpCode(name="div_s_32", fn=cls.div_s_32, gas=1, is_terminating=False),
            195: OpCode(name="rem_u_32", fn=cls.rem_u_32, gas=1, is_terminating=False),
            196: OpCode(name="rem_s_32", fn=cls.rem_s_32, gas=1, is_terminating=False),
            197: OpCode(
                name="shlo_l_32", fn=cls.shlo_l_32, gas=1, is_terminating=False
            ),
            198: OpCode(
                name="shlo_r_32", fn=cls.shlo_r_32, gas=1, is_terminating=False
            ),
            199: OpCode(
                name="shar_r_32", fn=cls.shar_r_32, gas=1, is_terminating=False
            ),
            200: OpCode(name="add_64", fn=cls.add_64, gas=1, is_terminating=False),
            201: OpCode(name="sub_64", fn=cls.sub_64, gas=1, is_terminating=False),
            202: OpCode(name="mul_64", fn=cls.mul_64, gas=1, is_terminating=False),
            203: OpCode(name="div_u_64", fn=cls.div_u_64, gas=1, is_terminating=False),
            204: OpCode(name="div_s_64", fn=cls.div_s_64, gas=1, is_terminating=False),
            205: OpCode(name="rem_u_64", fn=cls.rem_u_64, gas=1, is_terminating=False),
            206: OpCode(name="rem_s_64", fn=cls.rem_s_64, gas=1, is_terminating=False),
            207: OpCode(
                name="shlo_l_64", fn=cls.shlo_l_64, gas=1, is_terminating=False
            ),
            208: OpCode(
                name="shlo_r_64", fn=cls.shlo_r_64, gas=1, is_terminating=False
            ),
            209: OpCode(
                name="shar_r_64", fn=cls.shar_r_64, gas=1, is_terminating=False
            ),
            210: OpCode(name="and", fn=cls._op("and"), gas=1, is_terminating=False),
            211: OpCode(name="xor", fn=cls._op("xor"), gas=1, is_terminating=False),
            212: OpCode(name="or", fn=cls._op("or"), gas=1, is_terminating=False),
            213: OpCode(
                name="mul_upper_s_s", fn=cls.mul_upper_s_s, gas=1, is_terminating=False
            ),
            214: OpCode(
                name="mul_upper_u_u", fn=cls.mul_upper_u_u, gas=1, is_terminating=False
            ),
            215: OpCode(
                name="mul_upper_s_u", fn=cls.mul_upper_s_u, gas=1, is_terminating=False
            ),
            216: OpCode(name="set_lt_u", fn=cls.set_lt_u, gas=1, is_terminating=False),
            217: OpCode(name="set_lt_s", fn=cls.set_lt_s, gas=1, is_terminating=False),
            218: OpCode(name="cmov_iz", fn=cls.cmov_iz, gas=1, is_terminating=False),
            219: OpCode(name="cmov_nz", fn=cls.cmov_nz, gas=1, is_terminating=False),
            220: OpCode(name="rot_l_64", fn=cls.rot_l_64, gas=1, is_terminating=False),
            221: OpCode(name="rot_l_32", fn=cls.rot_l_32, gas=1, is_terminating=False),
            222: OpCode(name="rot_r_64", fn=cls.rot_r(64), gas=1, is_terminating=False),
            223: OpCode(name="rot_r_32", fn=cls.rot_r(32), gas=1, is_terminating=False),
            224: OpCode(
                name="and_inv",
                fn=cls._op("and", inv_b=True),
                gas=1,
                is_terminating=False,
            ),
            225: OpCode(
                name="or_inv", fn=cls._op("or", inv_b=True), gas=1, is_terminating=False
            ),
            226: OpCode(
                name="xnor",
                fn=cls._op("xor", inv_res=True),
                gas=1,
                is_terminating=False,
            ),
            227: OpCode(name="max", fn=cls._max, gas=1, is_terminating=False),
            228: OpCode(name="max_u", fn=cls._max_u, gas=1, is_terminating=False),
            229: OpCode(name="min", fn=cls._min, gas=1, is_terminating=False),
            230: OpCode(name="min_u", fn=cls._min_u, gas=1, is_terminating=False),
        }

    def add_32(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = chi(
            (int(registers[ra]) + int(registers[rb])) % 2**32, 4
        )
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def add_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = (int(registers[ra]) + int(registers[rb])) % 2**64
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def sub_32(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = chi(
            (registers[ra] + 2**32 - (registers[rb] % 2**32)) % 2**32, 4
        )
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def sub_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = (registers[ra] + 2**64 - registers[rb]) % 2**64
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def mul_32(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = chi((registers[ra] * registers[rb]) % 2**32, 4)
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def mul_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = (int(registers[ra]) * int(registers[rb])) % 2**64
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def div_u_32(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        if (registers[rb] % 2**32) == 0:
            value = 2**64 - 1
        else:
            value = chi((registers[ra] % 2**32) // (registers[rb] % 2**32), 4)

        registers[rd] = value
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def div_u_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        if registers[rb] == 0:
            value = 2**64 - 1
        else:
            value = trunc(Decimal(int(registers[ra])) / int(registers[rb]))

        registers[rd] = value
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def div_s_32(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        a = z(registers[ra] % 2**32, 4)
        b = z(registers[rb] % 2**32, 4)
        if b == 0:
            value = 2**64 - 1
        elif a == -(2**31) and b == -1:
            value = z_inv(a, 8)
        else:
            value = z_inv(trunc(a / b), 8)

        registers[rd] = value
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def div_s_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        if registers[rb] == 0:
            value = 2**64 - 1
        else:
            a = z(registers[ra], 8)
            b = z(registers[rb], 8)
            if a == -(2**63) and b == -1:
                value = registers[ra]
            else:
                value = z_inv(trunc(Decimal(a) / b), 8)

        registers[rd] = value
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def rem_u_32(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        a = registers[ra] % 2**32
        b = registers[rb] % 2**32
        registers[rd] = chi(a if b == 0 else a % b, 4)
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def rem_u_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        a = registers[ra]
        b = registers[rb]
        registers[rd] = a if b == 0 else a % b
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def rem_s_32(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        a = z(registers[ra] % 2**32, 4)
        b = z(registers[rb] % 2**32, 4)
        if a == -(2**31) and b == -1:
            registers[rd] = 0
        else:
            registers[rd] = z_inv(smod(a, b), 8)
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def rem_s_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        a = z(registers[ra], 8)
        b = z(registers[rb], 8)
        if a == -(2**31) and b == -1:
            registers[rd] = 0
        else:
            registers[rd] = z_inv(smod(a, b), 8)
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def shlo_l_32(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = chi(
            (int(registers[ra]) * 2 ** (int(registers[rb]) % 32)) % 2**32, 4
        )
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def shlo_l_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = (
            int(registers[ra]) * 2 ** (int(registers[rb]) % 64)
        ) % 2**64
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def shlo_r_32(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = chi(
            (registers[ra] % 2**32) // 2 ** (int(registers[rb]) % 32), 4
        )
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def shlo_r_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = (int(registers[ra]) % 2**64) // 2 ** (
            int(registers[rb]) % 64
        )
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def shar_r_32(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = z_inv(
            z(registers[ra] % 2**32, 4) // 2 ** (int(registers[rb]) % 32), 8
        )
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def shar_r_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = z_inv(
            z(registers[ra] % 2**64, 8) // 2 ** (int(registers[rb]) % 64), 8
        )
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    @staticmethod
    def _op(op: str, inv_a: bool=False, inv_b: bool=False, inv_res: bool=False) -> Callable[["InstructionsWArgs3Reg", List[int], Memory, int, int, int], OpReturn]:
        def op_impl(self: InstructionsWArgs3Reg, registers: List[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
            ba = b(int(registers[ra]), 8)
            bb = b(int(registers[rb]), 8)
            
            # Apply inversions if needed
            if inv_a:
                ba = [not bit for bit in ba]
            if inv_b:
                bb = [not bit for bit in bb]
            
            # Use vectorized comparison for massive performance boost
            result = compare_bits_vectorized(ba, bb, op)
            
            # Apply result inversion if needed
            if inv_res:
                result = [not bit for bit in result]
                
            registers[rd] = b_inv(result)
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return op_impl

    def mul_upper_s_s(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = z_inv(
            z(registers[ra], 8) * z(registers[rb], 8) // 2**64, 8
        )

        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def mul_upper_u_u(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = (
            int(registers[ra]) * int(registers[rb])
        ) // 2**64
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def mul_upper_s_u(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = z_inv(
            z(int(registers[ra]), 8) * int(registers[rb]) // 2**64, 8
        )

        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def set_lt_u(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = int(registers[ra] < registers[rb])
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def set_lt_s(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = int(z(registers[ra], 8) < z(registers[rb], 8))
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def cmov_iz(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        if registers[rb] == 0:
            registers[rd] = registers[ra]
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def cmov_nz(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        if registers[rb] != 0:
            registers[rd] = registers[ra]
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def _max(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = z_inv(
            max(z(registers[ra], 8), z(registers[rb], 8)), 8
        )

        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def _max_u(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = max(registers[ra], registers[rb])
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def _min(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = z_inv(
            min(z(registers[ra], 8), z(registers[rb], 8)), 8
        )
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def _min_u(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        registers[rd] = min(registers[ra], registers[rb])
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    def rot_l_64(self, registers: list[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        x = [0] * 64
        ba = b(registers[ra], 8)
        for i in range(64):
            x[(i + int(registers[rb])) % 64] = ba[i]
        registers[rd] = b_inv(x)
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory

    @staticmethod
    def rot_r(bitsize: int) -> Callable[["InstructionsWArgs3Reg", List[int], Memory, int, int, int], OpReturn]:
        def rot_r_impl(self: InstructionsWArgs3Reg, registers: List[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
            a_bits = b(int(registers[ra]) % 2 ** (bitsize), bitsize // 8)
            b_val = registers[rb] % 2 ** (bitsize)
            x = b_inv([a_bits[(i + b_val) % bitsize] for i in range(bitsize)])
            if bitsize < 64:
                x = chi(x, bitsize // 8)
            registers[rd] = x
            return CONTINUE, self.counter + self.skip_index + 1, registers, memory

        return rot_r_impl

    def rot_l_32(self, registers: List[int], memory: Memory, ra: int, rb: int, rd: int) -> OpReturn:
        x: List[int] = [0] * 32
        ba = b(int(registers[ra]) % 2**32, 4)
        for i in range(32):
            x[(i + int(registers[rb])) % 32] = ba[i]
        registers[rd] = chi(b_inv(x), 4)
        return CONTINUE, self.counter + self.skip_index + 1, registers, memory
