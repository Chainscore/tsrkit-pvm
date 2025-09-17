# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 2 register + 1 offset argument instructions.

This table handles instructions that take two registers and one offset argument:
- branch_eq/ne/lt_u/ge_u/lt_s/ge_s: Conditional branch with offset
"""

from typing import Dict
cimport cython
from libc.stdint cimport uint32_t, int64_t, uint64_t

from tsrkit_pvm.core.opcode import OpCode
from tsrkit_pvm.common.status import CONTINUE, PANIC
from tsrkit_pvm.common.utils import clamp_12, clamp_4_max0, z

cdef class CyInstructionsWArgs2Reg1Offset:
    """Cython optimized instruction class for 2 register + 1 offset instructions."""
    
    cdef public object program
    cdef public uint32_t counter
    cdef public uint32_t skip_index
    
    def __init__(self, program, counter, skip_index):
        self.program = program
        self.counter = counter  
        self.skip_index = skip_index

    cpdef list get_props(self):
        """Extract register indices and offset value from the instruction."""
        cdef bytes zeta_slice = self.program.zeta[self.counter + 1:self.counter + 7]
        cdef uint32_t byte_val = zeta_slice[0]
        
        cdef uint32_t ra = clamp_12(byte_val & 0x0F)  # Lower 4 bits
        cdef uint32_t rb = clamp_12(byte_val >> 4)    # Upper 4 bits
        cdef uint32_t lx = clamp_4_max0(self.skip_index - 1)
        
        cdef uint64_t vx
        cdef bytes offset_slice
        cdef uint32_t raw_offset
        if lx > 0:
            offset_slice = zeta_slice[1:1+lx]
            raw_offset = int.from_bytes(offset_slice, "little")
            vx = int(self.counter) + z(raw_offset, lx)
        else:
            vx = int(self.counter)
        
        return [ra, rb, lx, vx]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            170: OpCode(name="branch_eq", fn=cls.branch_eq, gas=1, is_terminating=True),
            171: OpCode(name="branch_ne", fn=cls.branch_ne, gas=1, is_terminating=True),
            172: OpCode(name="branch_lt_u", fn=cls.branch_lt_u, gas=1, is_terminating=True),
            173: OpCode(name="branch_lt_s", fn=cls.branch_lt_s, gas=1, is_terminating=True),
            174: OpCode(name="branch_ge_u", fn=cls.branch_ge_u, gas=1, is_terminating=True),
            175: OpCode(name="branch_ge_s", fn=cls.branch_ge_s, gas=1, is_terminating=True),
        }

    cpdef tuple branch_eq(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC170: Branch if ra == rb to offset vx."""
        cdef object status_result
        cdef object status
        cdef uint32_t target_counter
        if registers[ra] == registers[rb]:
            status_result = self.program.branch(self.counter, vx, True)
            status = status_result[0]
            target_counter = status_result[1]
            if status == CONTINUE and target_counter != self.counter:
                return status, target_counter, registers, memory
        
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple branch_ne(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC171: Branch if ra != rb to offset vx."""
        cdef object status_result
        cdef object status
        cdef uint32_t target_counter
        if registers[ra] != registers[rb]:
            status_result = self.program.branch(self.counter, vx, True)
            status = status_result[0]
            target_counter = status_result[1]
            if status == CONTINUE and target_counter != self.counter:
                return status, target_counter, registers, memory
        
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple branch_lt_u(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC172: Branch if ra < rb (unsigned) to offset vx."""
        cdef object status_result
        cdef object status
        cdef uint32_t target_counter
        if registers[ra] < registers[rb]:
            status_result = self.program.branch(self.counter, vx, True)
            status = status_result[0]
            target_counter = status_result[1]
            if status == CONTINUE and target_counter != self.counter:
                return status, target_counter, registers, memory
        
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple branch_lt_s(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC173: Branch if ra < rb (signed) to offset vx."""
        cdef object status_result
        cdef object status
        cdef uint32_t target_counter
        if registers[ra] < registers[rb]:
            status_result = self.program.branch(self.counter, vx, True)
            status = status_result[0]
            target_counter = status_result[1]
            if status == CONTINUE and target_counter != self.counter:
                return status, target_counter, registers, memory
        
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple branch_ge_u(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC174: Branch if ra >= rb (unsigned) to offset vx."""
        cdef uint64_t a = registers[ra]
        cdef uint64_t b = registers[rb]
        cdef object status_result
        cdef object status
        cdef uint32_t target_counter
        if a >= b:
            status_result = self.program.branch(self.counter, vx, True)
            status = status_result[0]
            target_counter = status_result[1]
            if status == CONTINUE and target_counter != self.counter:
                return status, target_counter, registers, memory
        
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple branch_ge_s(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint64_t vx):
        """OPC175: Branch if ra >= rb (signed) to offset vx."""
        cdef int64_t a = <int64_t>registers[ra]
        cdef int64_t b = <int64_t>registers[rb]
        cdef object status_result
        cdef object status
        cdef uint32_t target_counter
        if a >= b:
            status_result = self.program.branch(self.counter, vx, True)
            status = status_result[0]
            target_counter = status_result[1]
            if status == CONTINUE and target_counter != self.counter:
                return status, target_counter, registers, memory
        
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory
