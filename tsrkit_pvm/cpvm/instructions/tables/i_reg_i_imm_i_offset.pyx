# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 1 register + 1 immediate + 1 offset argument instructions.

This table handles instructions that take one register, one immediate, and one offset argument:
- load_imm_jump: Load immediate and jump
- branch_eq_imm/ne_imm: Branch if register equals/not equals immediate
"""

from typing import Dict
cimport cython
from libc.stdint cimport uint32_t, uint64_t, int64_t

from tsrkit_pvm.core.opcode import OpCode
from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import chi, z, clamp_12, clamp_4, clamp_4_max0, compare
from ...cy_memory cimport CyMemory


cdef class InstructionsWArgs1Reg1Imm1Offset:
    """Cython optimized instruction class for 1 register + 1 immediate + 1 offset instructions."""
    
    cdef public object program
    cdef public uint32_t counter
    cdef public uint32_t skip_index
    
    def __init__(self, counter, program, skip_index):
        self.counter = counter
        self.program = program  
        self.skip_index = skip_index

    cpdef list get_props(self):
        """Extract register index, immediate value, and offset from the instruction."""
        cdef bytes zeta_slice = self.program.zeta[self.counter + 1:self.counter + 8]
        cdef uint32_t byte_val = zeta_slice[0]
        
        cdef uint32_t ra = clamp_12(byte_val & 0x0F)           # Lower 4 bits
        cdef uint32_t lx = clamp_4((byte_val >> 4) & 0x07)     # Next 3 bits
        cdef uint32_t ly = clamp_4_max0(int(self.skip_index) - lx - 1)
        
        cdef uint64_t vx = 0
        cdef bytes imm1_slice
        if lx > 0:
            imm1_slice = zeta_slice[1:1+lx]
            vx = chi(int.from_bytes(imm1_slice, "little"), lx)
        
        cdef uint64_t vy = int(self.counter)
        cdef bytes imm2_slice
        if ly > 0:
            imm2_slice = zeta_slice[1+lx:1+lx+ly]
            vy = int(self.counter) + z(int.from_bytes(imm2_slice, "little"), ly)
        
        return [ra, lx, ly, vx, vy]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            80: OpCode(name="load_imm_jump", fn=cls.load_imm_jump, gas=1, is_terminating=True),
            81: OpCode(name="branch_eq_imm", fn=cls.branch_imm("eq"), gas=1, is_terminating=True),
            82: OpCode(name="branch_ne_imm", fn=cls.branch_imm("ne"), gas=1, is_terminating=True),
            83: OpCode(name="branch_lt_u_imm", fn=cls.branch_imm("lt"), gas=1, is_terminating=True),
            84: OpCode(name="branch_le_u_imm", fn=cls.branch_imm("le"), gas=1, is_terminating=True),
            85: OpCode(name="branch_ge_u_imm", fn=cls.branch_imm("ge"), gas=1, is_terminating=True),
            86: OpCode(name="branch_gt_u_imm", fn=cls.branch_imm("gt"), gas=1, is_terminating=True),
            87: OpCode(name="branch_lt_s_imm", fn=cls.branch_imm("lt", True), gas=1, is_terminating=True),
            88: OpCode(name="branch_le_s_imm", fn=cls.branch_imm("le", True), gas=1, is_terminating=True),
            89: OpCode(name="branch_ge_s_imm", fn=cls.branch_imm("ge", True), gas=1, is_terminating=True),
            90: OpCode(name="branch_gt_s_imm", fn=cls.branch_imm("gt", True), gas=1, is_terminating=True),
        }


    cdef tuple load_imm_jump(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC80: Load immediate value into register and jump to offset."""
        registers[ra] = vx
        status_result = self.program.branch(self.counter, vy, True)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1

    cdef tuple branch_eq_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC81: Branch if register equals immediate."""
        cdef bint condition = registers[ra] == vx
        status_result = self.program.branch(self.counter, vy, condition)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1

    cdef tuple branch_ne_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC82: Branch if register not equals immediate."""
        cdef bint condition = registers[ra] != vx
        status_result = self.program.branch(self.counter, vy, condition)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1

    cdef tuple branch_lt_u_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC83: Branch if register less than immediate (unsigned)."""
        cdef bint condition = registers[ra] < vx
        status_result = self.program.branch(self.counter, vy, condition)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1

    cdef tuple branch_le_u_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC84: Branch if register less than or equal immediate (unsigned)."""
        cdef bint condition = registers[ra] <= vx
        status_result = self.program.branch(self.counter, vy, condition)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1

    cdef tuple branch_ge_u_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC85: Branch if register greater than or equal immediate (unsigned)."""
        cdef bint condition = registers[ra] >= vx
        status_result = self.program.branch(self.counter, vy, condition)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1

    cdef tuple branch_gt_u_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC86: Branch if register greater than immediate (unsigned)."""
        cdef bint condition = registers[ra] > vx
        status_result = self.program.branch(self.counter, vy, condition)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1

    cdef tuple branch_lt_s_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC87: Branch if register less than immediate (signed)."""
        cdef bint condition = <int64_t>registers[ra] < <int64_t>vx
        status_result = self.program.branch(self.counter, vy, condition)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1

    cdef tuple branch_le_s_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC88: Branch if register less than or equal immediate (signed)."""
        cdef bint condition = <int64_t>registers[ra] <= <int64_t>vx
        status_result = self.program.branch(self.counter, vy, condition)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1

    cdef tuple branch_ge_s_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC89: Branch if register greater than or equal immediate (signed)."""
        cdef bint condition = <int64_t>registers[ra] >= <int64_t>vx
        status_result = self.program.branch(self.counter, vy, condition)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1

    cdef tuple branch_gt_s_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC90: Branch if register greater than immediate (signed)."""
        cdef bint condition = <int64_t>registers[ra] > <int64_t>vx
        status_result = self.program.branch(self.counter, vy, condition)
        status = status_result[0]
        counter = status_result[1]
        if status == CONTINUE and counter != self.counter:
            return status, counter
        return CONTINUE, -1
