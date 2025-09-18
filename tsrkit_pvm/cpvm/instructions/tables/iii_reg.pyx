# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

from typing import Dict
from libc.stdint cimport uint32_t, int64_t, uint32_t, uint64_t
from math import trunc
from decimal import Decimal
from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import clamp_12, smod, z, z_inv, chi
from tsrkit_pvm.core.opcode import OpCode, OpReturn
from ...cy_memory cimport CyMemory


cdef class CyInstructionsWArgs3Reg:
    """
    Cython optimized instruction table for instructions with 3 register arguments.
    """
    cdef uint32_t counter
    cdef object program
    cdef uint32_t skip_index
    
    def __init__(self, uint32_t counter, object program, uint32_t skip_index):
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    cpdef list get_props(self):
        """
        Extract 3 register indices from program bytes.
        Returns [ra, rb, rd] where ra and rb are sources, rd is destination.
        """
        cdef bytes zeta_slice = self.program.zeta[self.counter + 1:self.counter + 3]
        cdef uint32_t byte_val = zeta_slice[0]
        cdef uint32_t ra = clamp_12(byte_val & 0x0F)  # Lower 4 bits
        cdef uint32_t rb = clamp_12(byte_val >> 4)    # Upper 4 bits  
        cdef uint32_t rd = clamp_12(zeta_slice[1])    # Third register
        return [ra, rb, rd]
    
    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            # 32-bit arithmetic
            190: OpCode(name="add_32", fn=cls.add_32, gas=1, is_terminating=False),
            191: OpCode(name="sub_32", fn=cls.sub_32, gas=1, is_terminating=False),
            192: OpCode(name="mul_32", fn=cls.mul_32, gas=1, is_terminating=False),
            193: OpCode(name="div_u_32", fn=cls.div_u_32, gas=1, is_terminating=False),
            194: OpCode(name="div_s_32", fn=cls.div_s_32, gas=1, is_terminating=False),
            195: OpCode(name="rem_u_32", fn=cls.rem_u_32, gas=1, is_terminating=False),
            196: OpCode(name="rem_s_32", fn=cls.rem_s_32, gas=1, is_terminating=False),
            197: OpCode(name="shlo_l_32", fn=cls.shlo_l_32, gas=1, is_terminating=False),
            198: OpCode(name="shlo_r_32", fn=cls.shlo_r_32, gas=1, is_terminating=False),
            199: OpCode(name="shar_r_32", fn=cls.shar_r_32, gas=1, is_terminating=False),
            
            # 64-bit arithmetic  
            200: OpCode(name="add_64", fn=cls.add_64, gas=1, is_terminating=False),
            201: OpCode(name="sub_64", fn=cls.sub_64, gas=1, is_terminating=False),
            202: OpCode(name="mul_64", fn=cls.mul_64, gas=1, is_terminating=False),
            203: OpCode(name="div_u_64", fn=cls.div_u_64, gas=1, is_terminating=False),
            204: OpCode(name="div_s_64", fn=cls.div_s_64, gas=1, is_terminating=False),
            205: OpCode(name="rem_u_64", fn=cls.rem_u_64, gas=1, is_terminating=False),
            206: OpCode(name="rem_s_64", fn=cls.rem_s_64, gas=1, is_terminating=False),
            207: OpCode(name="shlo_l_64", fn=cls.shlo_l_64, gas=1, is_terminating=False),
            208: OpCode(name="shlo_r_64", fn=cls.shlo_r_64, gas=1, is_terminating=False),
            209: OpCode(name="shar_r_64", fn=cls.shar_r_64, gas=1, is_terminating=False),
            
            # Bitwise operations
            210: OpCode(name="and", fn=cls.and_op, gas=1, is_terminating=False),
            211: OpCode(name="xor", fn=cls.xor_op, gas=1, is_terminating=False),
            212: OpCode(name="or", fn=cls.or_op, gas=1, is_terminating=False),
            
            # Multiplication upper bits
            213: OpCode(name="mul_upper_s_s", fn=cls.mul_upper_s_s, gas=1, is_terminating=False),
            214: OpCode(name="mul_upper_u_u", fn=cls.mul_upper_u_u, gas=1, is_terminating=False),
            215: OpCode(name="mul_upper_s_u", fn=cls.mul_upper_s_u, gas=1, is_terminating=False),
            
            # Comparison operations  
            216: OpCode(name="set_lt_u", fn=cls.set_lt_u, gas=1, is_terminating=False),
            217: OpCode(name="set_lt_s", fn=cls.set_lt_s, gas=1, is_terminating=False),
            
            # Conditional move operations
            218: OpCode(name="cmov_iz", fn=cls.cmov_iz, gas=1, is_terminating=False),
            219: OpCode(name="cmov_nz", fn=cls.cmov_nz, gas=1, is_terminating=False),
            
            # Rotation operations
            220: OpCode(name="rot_l_64", fn=cls.rot_l_64, gas=1, is_terminating=False),
            221: OpCode(name="rot_l_32", fn=cls.rot_l_32, gas=1, is_terminating=False),
            222: OpCode(name="rot_r_64", fn=cls.rot_r_64, gas=1, is_terminating=False),
            223: OpCode(name="rot_r_32", fn=cls.rot_r_32, gas=1, is_terminating=False),
            
            # Inverted bitwise operations
            224: OpCode(name="and_inv", fn=cls.and_inv, gas=1, is_terminating=False),
            225: OpCode(name="or_inv", fn=cls.or_inv, gas=1, is_terminating=False),
            226: OpCode(name="xnor", fn=cls.xnor, gas=1, is_terminating=False),
            
            # Min/max operations
            227: OpCode(name="max", fn=cls.max_op, gas=1, is_terminating=False),
            228: OpCode(name="max_u", fn=cls.max_u, gas=1, is_terminating=False),
            229: OpCode(name="min", fn=cls.min_op, gas=1, is_terminating=False),
            230: OpCode(name="min_u", fn=cls.min_u, gas=1, is_terminating=False),
        }

    # 32-bit arithmetic operations with C-level optimizations
    cdef tuple  add_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC190: 32-bit addition."""
        registers[rd] = chi(
            (int(registers[ra]) + int(registers[rb])) % 2**32, 4
        )
        return CONTINUE, -1

    cdef tuple  sub_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC191: 32-bit subtraction."""
        registers[rd] = chi(
            (registers[ra] + 2**32 - (registers[rb] % 2**32)) % 2**32, 4
        )
        return CONTINUE, -1

    cdef tuple  mul_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC192: 32-bit multiplication."""
        registers[rd] = chi((registers[ra] * registers[rb]) % 2**32, 4)
        return CONTINUE, -1

    cdef tuple  div_u_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC193: 32-bit unsigned division."""
        if (registers[rb] % 2**32) == 0:
            value = 2**64 - 1
        else:
            value = chi((registers[ra] % 2**32) // (registers[rb] % 2**32), 4)

        registers[rd] = value
        return CONTINUE, -1

    cdef tuple  div_s_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC194: 32-bit signed division."""
        a = z(registers[ra] % 2**32, 4)
        b = z(registers[rb] % 2**32, 4)
        if b == 0:
            value = 2**64 - 1
        elif a == -(2**31) and b == -1:
            value = z_inv(a, 8)
        else:
            value = z_inv(trunc(a / b), 8)

        registers[rd] = value
        return CONTINUE, -1

    cdef tuple  rem_u_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC195: 32-bit unsigned remainder."""
        a = registers[ra] % 2**32
        b = registers[rb] % 2**32
        registers[rd] = chi(a if b == 0 else a % b, 4)
        return CONTINUE, -1

    cdef tuple rem_s_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC196: 32-bit signed remainder."""
        a = z(registers[ra] % 2**32, 4)
        b = z(registers[rb] % 2**32, 4)
        if a == -(2**31) and b == -1:
            registers[rd] = 0
        else:
            registers[rd] = z_inv(smod(a, b), 8)
        return CONTINUE, -1

    # 64-bit arithmetic operations  
    cdef tuple  add_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC200: 64-bit addition."""
        cdef uint64_t a = registers[ra]
        cdef uint64_t b = registers[rb]
        cdef uint64_t result = (a + b) % (2**64)
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  sub_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC201: 64-bit subtraction."""
        cdef uint64_t a = registers[ra]
        cdef uint64_t b = registers[rb]
        cdef uint64_t result = (a - b) % (2**64)
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  mul_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC202: 64-bit multiplication."""
        cdef uint64_t a = registers[ra]
        cdef uint64_t b = registers[rb]
        cdef uint64_t result = (a * b) % (2**64)
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  div_u_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC203: 64-bit unsigned division."""
        if registers[rb] == 0:
            value = 2**64 - 1
        else:
            value = trunc(Decimal(int(registers[ra])) / int(registers[rb]))

        registers[rd] = value
        return CONTINUE, -1

    cdef tuple  div_s_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC204: 64-bit signed division."""
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
        return CONTINUE, -1

    cdef tuple  rem_u_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC205: 64-bit unsigned remainder."""
        cdef uint64_t a = registers[ra]
        cdef uint64_t b = registers[rb]
        cdef uint64_t result = 0 if b == 0 else a % b
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  rem_s_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC206: 64-bit signed remainder."""
        a = z(registers[ra], 8)
        b = z(registers[rb], 8)
        if a == -(2**31) and b == -1:
            registers[rd] = 0
        else:
            registers[rd] = z_inv(smod(a, b), 8)
        return CONTINUE, -1

    # Shift operations
    cdef tuple  shlo_l_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC197: 32-bit logical left shift."""
        cdef uint32_t a = registers[ra] % (2**32)
        cdef uint32_t shift = registers[rb] % 32
        cdef uint32_t result = (a << shift) % (2**32)
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  shlo_r_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC198: 32-bit logical right shift."""
        registers[rd] = chi(
            (registers[ra] % 2**32) // 2 ** (int(registers[rb]) % 32), 4
        )
        return CONTINUE, -1

    cdef tuple  shar_r_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC199: 32-bit arithmetic shift right."""
        registers[rd] = z_inv(
            z(registers[ra] % 2**32, 4) // 2 ** (int(registers[rb]) % 32), 8
        )
        return CONTINUE, -1

    cdef tuple  shlo_l_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC207: 64-bit logical shift left."""
        registers[rd] = (
            int(registers[ra]) * 2 ** (int(registers[rb]) % 64)
        ) % 2**64
        return CONTINUE, -1

    cdef tuple  shlo_r_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC208: 64-bit logical shift right."""
        registers[rd] = (int(registers[ra]) % 2**64) // 2 ** (
            int(registers[rb]) % 64
        )
        return CONTINUE, -1

    cdef tuple  shar_r_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC209: 64-bit arithmetic shift right."""
        registers[rd] = z_inv(
            z(registers[ra] % 2**64, 8) // 2 ** (int(registers[rb]) % 64), 8
        )
        return CONTINUE, -1

    # Bitwise operations
    cdef tuple  and_op(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC210: Bitwise AND."""
        cdef uint64_t result = registers[ra] & registers[rb]
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  xor_op(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC211: Bitwise XOR."""
        cdef uint64_t result = registers[ra] ^ registers[rb]
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  or_op(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC212: Bitwise OR."""
        cdef uint64_t result = registers[ra] | registers[rb]
        registers[rd] = result
        return CONTINUE, -1

    # Multiplication upper bits
    cdef tuple  mul_upper_s_s(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC213: Signed multiplication upper 64 bits."""
        registers[rd] = z_inv(
            z(registers[ra], 8) * z(registers[rb], 8) // 2**64, 8
        )
        return CONTINUE, -1

    cdef tuple  mul_upper_u_u(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC214: Unsigned multiplication upper 64 bits."""
        registers[rd] = (
            int(registers[ra]) * int(registers[rb])
        ) // 2**64
        return CONTINUE, -1

    cdef tuple  mul_upper_s_u(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC215: Signed-unsigned multiplication upper 64 bits."""
        registers[rd] = z_inv(
            z(int(registers[ra]), 8) * int(registers[rb]) // 2**64, 8
        )

        return CONTINUE, -1

    # Comparison operations
    cdef tuple  set_lt_u(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC216: Set less than unsigned."""
        registers[rd] = int(registers[ra] < registers[rb])
        return CONTINUE, -1

    cdef tuple  set_lt_s(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC217: Set less than signed."""
        registers[rd] = int(z(registers[ra], 8) < z(registers[rb], 8))
        return CONTINUE, -1

    # Conditional move operations
    cdef tuple  cmov_iz(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC218: Conditional move if zero."""
        if registers[rb] == 0:
            registers[rd] = registers[ra]
        return CONTINUE, -1

    cdef tuple  cmov_nz(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC219: Conditional move if not zero."""
        if registers[rb] != 0:
            registers[rd] = registers[ra]
        return CONTINUE, -1

    # Rotation operations
    cdef tuple  rot_l_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC220: 64-bit rotate left."""
        cdef uint64_t value = registers[ra]
        cdef uint64_t amount = registers[rb] % 64
        cdef uint64_t result = ((value << amount) | (value >> (64 - amount))) & 0xFFFFFFFFFFFFFFFF
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  rot_l_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC221: 32-bit rotate left."""
        cdef uint32_t value = registers[ra] & 0xFFFFFFFF
        cdef uint32_t amount = registers[rb] % 32
        cdef uint32_t result = ((value << amount) | (value >> (32 - amount))) & 0xFFFFFFFF
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  rot_r_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC222: 64-bit rotate right."""
        cdef uint64_t value = registers[ra]
        cdef uint64_t amount = registers[rb] % 64
        cdef uint64_t result = ((value >> amount) | (value << (64 - amount))) & 0xFFFFFFFFFFFFFFFF
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  rot_r_32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC223: 32-bit rotate right."""
        cdef uint32_t value = registers[ra] & 0xFFFFFFFF
        cdef uint32_t amount = registers[rb] % 32
        cdef uint32_t result = ((value >> amount) | (value << (32 - amount))) & 0xFFFFFFFF
        registers[rd] = result
        return CONTINUE, -1

    # Inverted bitwise operations
    cdef tuple  and_inv(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC224: Bitwise AND with inverted rb."""
        cdef uint64_t result = registers[ra] & (~registers[rb])
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  or_inv(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC225: Bitwise OR with inverted rb."""
        cdef uint64_t result = registers[ra] | (~registers[rb])
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  xnor(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC226: Bitwise XNOR (XOR with inverted result)."""
        cdef uint64_t result = ~(registers[ra] ^ registers[rb])
        registers[rd] = result
        return CONTINUE, -1

    # Min/max operations
    cdef tuple  max_op(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC227: Maximum signed."""
        cdef int64_t a = <int64_t>registers[ra]
        cdef int64_t b = <int64_t>registers[rb]
        cdef uint64_t result = <uint64_t>(a if a > b else b)
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  max_u(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC228: Maximum unsigned."""
        cdef uint64_t a = registers[ra]
        cdef uint64_t b = registers[rb]
        cdef uint64_t result = a if a > b else b
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  min_op(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC229: Minimum signed."""
        cdef int64_t a = <int64_t>registers[ra]
        cdef int64_t b = <int64_t>registers[rb]
        cdef uint64_t result = <uint64_t>(a if a < b else b)
        registers[rd] = result
        return CONTINUE, -1

    cdef tuple  min_u(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t rb, uint32_t rd):
        """OPC230: Minimum unsigned."""
        cdef uint64_t a = registers[ra]
        cdef uint64_t b = registers[rb]
        cdef uint64_t result = a if a < b else b
        registers[rd] = result
        return CONTINUE, -1

