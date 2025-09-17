# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 2 register + 1 immediate argument instructions.

This table handles instructions that take two registers and one immediate argument:
- store_ind_u8/u16/u32/u64: Store indirect with offset
- load_ind_u8/i8/u16/i16/u32/i32/u64: Load indirect with offset
- add_imm/mul_imm/and_imm/xor_imm/or_imm: Arithmetic and logic with immediate
- set_lt/gt_u/s_imm: Comparison operations with immediate
- shlo_l/r_imm, shar_r_imm: Shift operations with immediate
- cmov_iz/nz_imm: Conditional moves with immediate
- rot_r_imm: Rotation operations with immediate
"""

from typing import Dict
from libc.stdint cimport uint32_t, int64_t, uint64_t
from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import b, b_inv, chi, compare, compare_bits_vectorized, z, z_inv, clamp_12, clamp_4, clamp_4_max0
from tsrkit_pvm.core.opcode import OpCode

cdef class CyInstructionsWArgs2Reg1Imm:
    """
    Cython optimized instruction table for 2 register + 1 immediate argument instructions.
    
    This class provides high-performance implementations of instructions that
    take two registers and one immediate argument, including:
    - Memory operations (store/load with offset)
    - Arithmetic operations with immediate values
    - Logic operations (AND, XOR, OR) with immediate values
    - Comparison and conditional operations
    - Shift and rotation operations
    All optimized with Cython for maximum performance.
    """
    
    cdef public uint32_t counter
    cdef public object program  # INT_Program - keeping as Python object for now
    cdef public uint32_t skip_index
    
    def __init__(self, uint32_t counter, program, uint32_t skip_index):
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    cpdef list get_props(self):
        """
        Extract two register and immediate arguments from the instruction stream.
        Returns [ra, rb, lx, vx] where ra/rb are registers, lx is length, vx is immediate.
        """
        cdef bytes zeta_slice = self.program.zeta[self.counter + 1:self.counter + 8]
        cdef uint32_t byte_val = zeta_slice[0]
        cdef uint32_t ra = clamp_12(byte_val & 0x0F)  # Lower 4 bits
        cdef uint32_t rb = clamp_12(byte_val >> 4)    # Upper 4 bits
        cdef uint32_t lx = clamp_4_max0(self.skip_index - 1)
        
        cdef uint64_t vx = 0  # Use temporary variable to handle overflow
        cdef bytes imm_slice
        if lx > 0:
            imm_slice = zeta_slice[1:1+lx]
            vx = <uint64_t>(chi(int.from_bytes(imm_slice, "little"), lx) % 2**64)
        
        return [ra, rb, lx, vx]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            120: OpCode(name="store_ind_u8", fn=cls.store_ind_u8, gas=1, is_terminating=False),
            121: OpCode(name="store_ind_u16", fn=cls.store_ind_u16, gas=1, is_terminating=False),
            122: OpCode(name="store_ind_u32", fn=cls.store_ind_u32, gas=1, is_terminating=False),
            123: OpCode(name="store_ind_u64", fn=cls.store_ind_u64, gas=1, is_terminating=False),
            124: OpCode(name="load_ind_u8", fn=cls.load_ind_u8, gas=1, is_terminating=False),
            125: OpCode(name="load_ind_i8", fn=cls.load_ind_i8, gas=1, is_terminating=False),
            126: OpCode(name="load_ind_u16", fn=cls.load_ind_u16, gas=1, is_terminating=False),
            127: OpCode(name="load_ind_i16", fn=cls.load_ind_i16, gas=1, is_terminating=False),
            128: OpCode(name="load_ind_u32", fn=cls.load_ind_u32, gas=1, is_terminating=False),
            129: OpCode(name="load_ind_i32", fn=cls.load_ind_i32, gas=1, is_terminating=False),
            130: OpCode(name="load_ind_u64", fn=cls.load_ind_u64, gas=1, is_terminating=False),
            131: OpCode(name="add_imm_32", fn=cls.add_imm_32, gas=1, is_terminating=False),
            132: OpCode(name="and_imm", fn=cls.and_imm, gas=1, is_terminating=False),
            133: OpCode(name="xor_imm", fn=cls.xor_imm, gas=1, is_terminating=False),
            134: OpCode(name="or_imm", fn=cls.or_imm, gas=1, is_terminating=False),
            135: OpCode(name="mul_imm_32", fn=cls.mul_imm_32, gas=1, is_terminating=False),
            136: OpCode(name="set_lt_u_imm", fn=cls.set_lt_u_imm, gas=1, is_terminating=False),
            137: OpCode(name="set_lt_s_imm", fn=cls.set_lt_s_imm, gas=1, is_terminating=False),
            138: OpCode(name="shlo_l_imm_32", fn=cls.shlo_l_imm_32, gas=1, is_terminating=False),
            139: OpCode(name="shlo_r_imm_32", fn=cls.shlo_r_imm_32, gas=1, is_terminating=False),
            140: OpCode(name="shar_r_imm_32", fn=cls.shar_r_imm_32, gas=1, is_terminating=False),
            141: OpCode(name="neg_add_imm_32", fn=cls.neg_add_imm_32, gas=1, is_terminating=False),
            142: OpCode(name="set_gt_u_imm", fn=cls.set_gt_u_imm, gas=1, is_terminating=False),
            143: OpCode(name="set_gt_s_imm", fn=cls.set_gt_s_imm, gas=1, is_terminating=False),
            144: OpCode(name="shlo_l_imm_alt_32", fn=cls.shlo_l_imm_alt_32, gas=1, is_terminating=False),
            145: OpCode(name="shlo_r_imm_alt_32", fn=cls.shlo_r_imm_alt_32, gas=1, is_terminating=False),
            146: OpCode(name="shar_r_imm_alt_32", fn=cls.shar_r_imm_alt_32, gas=1, is_terminating=False),
            147: OpCode(name="cmov_iz_imm", fn=cls.cmov_iz_imm, gas=1, is_terminating=False),
            148: OpCode(name="cmov_nz_imm", fn=cls.cmov_nz_imm, gas=1, is_terminating=False),
            149: OpCode(name="add_imm_64", fn=cls.add_imm_64, gas=1, is_terminating=False),
            150: OpCode(name="mul_imm_64", fn=cls.mul_imm_64, gas=1, is_terminating=False),
            151: OpCode(name="shlo_l_imm_64", fn=cls.shlo_l_imm_64, gas=1, is_terminating=False),
            152: OpCode(name="shlo_r_imm_64", fn=cls.shlo_r_imm_64, gas=1, is_terminating=False),
            153: OpCode(name="shar_r_imm_64", fn=cls.shar_r_imm_64, gas=1, is_terminating=False),
            154: OpCode(name="neg_add_imm_64", fn=cls.neg_add_imm_64, gas=1, is_terminating=False),
            155: OpCode(name="shlo_l_imm_alt_64", fn=cls.shlo_l_imm_alt_64, gas=1, is_terminating=False),
            156: OpCode(name="shlo_r_imm_alt_64", fn=cls.shlo_r_imm_alt_64, gas=1, is_terminating=False),
            157: OpCode(name="shar_r_imm_alt_64", fn=cls.shar_r_imm_alt_64, gas=1, is_terminating=False),
            158: OpCode(name="rot_r_64_imm", fn=cls.rot_r_64_imm, gas=1, is_terminating=False),
            159: OpCode(name="rot_r_64_imm_alt", fn=cls.rot_r_64_imm_alt, gas=1, is_terminating=False),
            160: OpCode(name="rot_r_32_imm", fn=cls.rot_r_32_imm, gas=1, is_terminating=False),
            161: OpCode(name="rot_r_32_imm_alt", fn=cls.rot_r_32_imm_alt, gas=1, is_terminating=False),
        }

    # Store indirect instructions
    cpdef tuple store_ind_u8(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC120: Store register ra as u8 to address (rb + vx)."""
        value = int(registers[ra] & 0xFF)
        memory.write(registers[rb] + vx, value.to_bytes(1, "little"))
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple store_ind_u16(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC121: Store register ra as u16 to address (rb + vx)."""
        value = int(registers[ra] & 0xFFFF)
        memory.write(registers[rb] + vx, value.to_bytes(2, "little"))
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple store_ind_u32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC122: Store register ra as u32 to address (rb + vx)."""
        value = int(registers[ra] % 2**32)
        memory.write(registers[rb] + vx, value.to_bytes(4, "little"))
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple store_ind_u64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC123: Store register ra as u64 to address (rb + vx)."""
        value = int(registers[ra])
        
        memory.write(registers[rb] + vx, value.to_bytes(8, "little"))
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    # Load indirect instructions
    cpdef tuple load_ind_u8(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC124: Load u8 from address (rb + vx) to register ra."""
        data = memory.read(registers[rb] + vx, 1)
        value = int.from_bytes(data, "little")
        registers[ra] = value
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple load_ind_i8(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC125: Load i8 from address (rb + vx) to register ra."""
        cdef bytes data = memory.read(registers[rb] + vx, 1)
        value = int.from_bytes(data, "little")
        # Sign extend from 8-bit to 64-bit
        value = z_inv(z(value, 1), 8)
        registers[ra] = value
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple load_ind_u16(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC126: Load u16 from address (rb + vx) to register ra."""
        cdef uint64_t address = <uint64_t>(registers[rb] + vx)
        data = memory.read(registers[rb] + vx, 2)
        value = int.from_bytes(data, "little")
        registers[ra] = value
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple load_ind_i16(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC127: Load i16 from address (rb + vx) to register ra."""
        cdef bytes data = memory.read(registers[rb] + vx, 2)
        value = int.from_bytes(data, "little")
        # Sign extend from 16-bit to 64-bit
        value = z_inv(z(value, 2), 8)
        registers[ra] = value
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple load_ind_u32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC128: Load u32 from address (rb + vx) to register ra."""
        data = memory.read(registers[rb] + vx, 4)
        value = int.from_bytes(data, "little")
        registers[ra] = value
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple load_ind_i32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC129: Load i32 from address (rb + vx) to register ra."""
        cdef bytes data = memory.read(registers[rb] + vx, 4)
        value = int.from_bytes(data, "little")
        # Sign extend from 32-bit to 64-bit
        value = z_inv(z(value, 4), 8)
        registers[ra] = value
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple load_ind_u64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC130: Load u64 from address (rb + vx) to register ra."""
        data = memory.read(registers[rb] + vx, 8)
        value = int.from_bytes(data, "little")
        registers[ra] = value
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    # Arithmetic and logic operations with immediate values
    cpdef tuple add_imm_32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC131: Add immediate value to register (32-bit)."""
        cdef uint64_t value = (registers[rb] + vx) % 2**32
        registers[ra] = chi(value, 4)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple and_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC132: Bitwise AND with immediate value."""
        cdef list wb_bits = b(registers[rb], 8)
        cdef list vx_bits = b(vx, 8)
        cdef list result_bits = compare_bits_vectorized(wb_bits, vx_bits, "and")
        registers[ra] = b_inv(result_bits)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple xor_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC133: Bitwise XOR with immediate value."""
        cdef list wb_bits = b(registers[rb], 8)
        cdef list vx_bits = b(vx, 8)
        cdef list result_bits = compare_bits_vectorized(wb_bits, vx_bits, "xor")
        registers[ra] = b_inv(result_bits)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple or_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC134: Bitwise OR with immediate value."""
        cdef list wb_bits = b(registers[rb], 8)
        cdef list vx_bits = b(vx, 8)
        cdef list result_bits = compare_bits_vectorized(wb_bits, vx_bits, "or")
        registers[ra] = b_inv(result_bits)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple mul_imm_32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC135: Multiply with immediate value (32-bit)."""
        cdef uint64_t value = (registers[rb] * vx) % 2**32
        registers[ra] = chi(value, 4)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple set_lt_u_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC136: Set if less than (unsigned) immediate."""
        registers[ra] = 1 if registers[rb] < vx else 0
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple set_lt_s_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC137: Set if less than (signed) immediate."""
        cdef int64_t a = z(registers[rb], 8)
        cdef int64_t b = z(vx, 8)
        registers[ra] = 1 if a < b else 0
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shlo_l_imm_32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC138: Shift left immediate (32-bit)."""
        cdef uint64_t a = registers[rb]
        cdef uint64_t shift = vx % 32
        cdef uint64_t result = (a * (2 ** shift)) % 2**32
        registers[ra] = chi(result, 4)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shlo_r_imm_32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC139: Shift right logical immediate (32-bit)."""
        cdef uint64_t a = registers[rb] % 2**32
        cdef uint64_t shift = vx % 32
        cdef uint64_t result = a >> shift
        registers[ra] = chi(result, 4)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shar_r_imm_32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC140: Shift right arithmetic immediate (32-bit)."""
        cdef int64_t a = z(registers[rb] % 2**32, 4)
        cdef uint64_t shift = vx % 32
        cdef int64_t result = a >> shift
        registers[ra] = z_inv(result, 8)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple neg_add_imm_32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC141: Negate and add immediate (32-bit)."""
        cdef uint64_t value = (vx + 2**32 - registers[rb]) % 2**32
        registers[ra] = chi(value, 4)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple set_gt_u_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC142: Set if greater than (unsigned) immediate."""
        registers[ra] = 1 if registers[rb] > vx else 0
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple set_gt_s_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC143: Set if greater than (signed) immediate."""
        cdef int64_t a = z(registers[rb], 8)
        cdef int64_t b = z(vx, 8)
        registers[ra] = 1 if a > b else 0
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shlo_l_imm_alt_32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC144: Shift left immediate alternate (32-bit) - operands swapped."""
        cdef uint64_t a = vx
        cdef uint64_t shift = registers[rb] % 32
        cdef uint64_t result = (a * (2 ** shift)) % 2**32
        registers[ra] = chi(result, 4)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shlo_r_imm_alt_32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC145: Shift right logical immediate alternate (32-bit) - operands swapped."""
        cdef uint64_t a = vx % 2**32
        cdef uint64_t shift = registers[rb] % 32
        cdef uint64_t result = a >> shift
        registers[ra] = chi(result, 4)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shar_r_imm_alt_32(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC146: Shift right arithmetic immediate alternate (32-bit) - operands swapped."""
        cdef int64_t a = z(vx % 2**32, 4)
        cdef uint64_t shift = registers[rb] % 32
        cdef int64_t result = a >> shift
        registers[ra] = z_inv(result, 8)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple cmov_iz_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC147: Conditional move if zero immediate."""
        if registers[rb] == 0:
            registers[ra] = vx
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple cmov_nz_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC148: Conditional move if not zero immediate."""
        if registers[rb] != 0:
            registers[ra] = vx
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    # 64-bit operations
    cpdef tuple add_imm_64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC149: Add immediate value to register (64-bit)."""
        registers[ra] = (registers[rb] + vx) % 2**64
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple mul_imm_64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC150: Multiply with immediate value (64-bit)."""
        registers[ra] = registers[rb] * vx
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shlo_l_imm_64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC151: Shift left immediate (64-bit)."""
        cdef uint64_t a = registers[rb]
        cdef uint64_t shift = vx % 64
        cdef uint64_t result = (a << shift) % 2**64
        registers[ra] = result
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shlo_r_imm_64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC152: Shift right logical immediate (64-bit)."""
        cdef uint64_t a = registers[rb]
        cdef uint64_t shift = vx % 64
        cdef uint64_t result = a >> shift
        registers[ra] = result
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shar_r_imm_64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC153: Shift right arithmetic immediate (64-bit)."""
        cdef int64_t a = <int64_t>registers[rb]
        cdef uint64_t shift = vx % 64
        cdef int64_t result = a >> shift
        registers[ra] = <uint64_t>result
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple neg_add_imm_64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC154: Negate and add immediate (64-bit)."""
        cdef uint64_t value = (vx + 2**64 - registers[rb]) % 2**64
        registers[ra] = value
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shlo_l_imm_alt_64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC155: Shift left immediate alternate (64-bit) - operands swapped."""
        cdef uint64_t a = vx
        cdef uint64_t shift = registers[rb] % 64
        cdef uint64_t result = (a << shift) % 2**64
        registers[ra] = result
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shlo_r_imm_alt_64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC156: Shift right logical immediate alternate (64-bit) - operands swapped."""
        cdef uint64_t a = vx
        cdef uint64_t shift = registers[rb] % 64
        cdef uint64_t result = a >> shift
        registers[ra] = result
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple shar_r_imm_alt_64(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC157: Shift right arithmetic immediate alternate (64-bit) - operands swapped."""
        cdef int64_t a = <int64_t>vx
        cdef uint64_t shift = registers[rb] % 64
        cdef int64_t result = a >> shift
        registers[ra] = <uint64_t>result
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    # Rotation operations
    cpdef tuple rot_r_64_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC158: Rotate right 64-bit immediate."""
        cdef uint64_t a_val = registers[rb]
        cdef uint64_t b_val = vx % 64
        cdef list a_bits = b(a_val, 8)
        cdef list result_bits = [a_bits[(i + b_val) % 64] for i in range(64)]
        registers[ra] = b_inv(result_bits)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple rot_r_64_imm_alt(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC159: Rotate right 64-bit immediate alternate - operands swapped."""
        cdef uint64_t a_val = vx
        cdef uint64_t b_val = registers[rb] % 64
        cdef list a_bits = b(a_val, 8)
        cdef list result_bits = [a_bits[(i + b_val) % 64] for i in range(64)]
        registers[ra] = b_inv(result_bits)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple rot_r_32_imm(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC160: Rotate right 32-bit immediate."""
        cdef uint64_t a_val = registers[rb] % 2**32
        cdef uint64_t b_val = vx % 32
        cdef list a_bits = b(a_val, 4)
        cdef list result_bits = [a_bits[(i + b_val) % 32] for i in range(32)]
        cdef uint64_t result = b_inv(result_bits)
        registers[ra] = chi(result, 4)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple rot_r_32_imm_alt(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC161: Rotate right 32-bit immediate alternate - operands swapped."""
        cdef uint64_t a_val = vx % 2**32
        cdef uint64_t b_val = registers[rb] % 32
        cdef list a_bits = b(a_val, 4)
        cdef list result_bits = [a_bits[(i + b_val) % 32] for i in range(32)]
        cdef uint64_t result = b_inv(result_bits)
        registers[ra] = chi(result, 4)
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

