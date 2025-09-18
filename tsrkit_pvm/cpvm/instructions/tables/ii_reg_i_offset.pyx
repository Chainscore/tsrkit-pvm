# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 2 register + 1 offset argument instructions.

This table handles instructions that take two registers and one offset argument:
- branch_eq/ne/lt_u/ge_u/lt_s/ge_s: Conditional branch with offset
"""

cimport cython
from libc.stdint cimport uint32_t, int64_t, uint64_t, uint8_t

from tsrkit_pvm.common.status import CONTINUE, PANIC
from tsrkit_pvm.common.utils import clamp_12, clamp_4_max0, z
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram


cdef tuple branch_eq_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC170: Branch if ra == rb to offset vx."""
    cdef object status_result
    cdef object status
    cdef uint32_t target_counter
    if registers[ra] == registers[rb]:
        status_result = program.branch(counter, vx, True)
        status = status_result[0]
        target_counter = status_result[1]
        if status == CONTINUE and target_counter != counter:
            return status, target_counter
    
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_ne_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC171: Branch if ra != rb to offset vx."""
    cdef object status_result
    cdef object status
    cdef uint32_t target_counter
    if registers[ra] != registers[rb]:
        status_result = program.branch(counter, vx, True)
        status = status_result[0]
        target_counter = status_result[1]
        if status == CONTINUE and target_counter != counter:
            return status, target_counter
    
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_lt_u_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC172: Branch if ra < rb (unsigned) to offset vx."""
    cdef object status_result
    cdef object status
    cdef uint32_t target_counter
    if registers[ra] < registers[rb]:
        status_result = program.branch(counter, vx, True)
        status = status_result[0]
        target_counter = status_result[1]
        if status == CONTINUE and target_counter != counter:
            return status, target_counter
    
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_lt_s_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC173: Branch if ra < rb (signed) to offset vx."""
    cdef object status_result
    cdef object status
    cdef uint32_t target_counter
    if registers[ra] < registers[rb]:
        status_result = program.branch(counter, vx, True)
        status = status_result[0]
        target_counter = status_result[1]
        if status == CONTINUE and target_counter != counter:
            return status, target_counter
    
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_ge_u_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC174: Branch if ra >= rb (unsigned) to offset vx."""
    cdef uint64_t a = registers[ra]
    cdef uint64_t b = registers[rb]
    cdef object status_result
    cdef object status
    cdef uint32_t target_counter
    if a >= b:
        status_result = program.branch(counter, vx, True)
        status = status_result[0]
        target_counter = status_result[1]
        if status == CONTINUE and target_counter != counter:
            return status, target_counter
    
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_ge_s_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC175: Branch if ra >= rb (signed) to offset vx."""
    cdef int64_t a = <int64_t>registers[ra]
    cdef int64_t b = <int64_t>registers[rb]
    cdef object status_result
    cdef object status
    cdef uint32_t target_counter
    if a >= b:
        status_result = program.branch(counter, vx, True)
        status = status_result[0]
        target_counter = status_result[1]
        if status == CONTINUE and target_counter != counter:
            return status, target_counter
    
    return CONTINUE, <uint32_t>0xFFFFFFFF


cdef class CyInstructionsWArgs2Reg1Offset(CyTable):
    """
    Cython optimized instruction table for instructions with 2 register + 1 offset argument.
    """
    
    cpdef tuple get_props(self, uint32_t program_counter, CyProgram program):
        """
        Extract register indices and offset value from program bytes.
        Returns (vx, vy, ra, rb, rd) where vx is offset, ra/rb are registers, others are 0.
        """
        cdef uint32_t skip_index = program.skip(program_counter)
        cdef bytes zeta_slice = program.zeta[program_counter + 1:program_counter + 7]
        cdef uint32_t byte_val = zeta_slice[0]
        
        cdef uint8_t ra = clamp_12(byte_val & 0x0F)  # Lower 4 bits
        cdef uint8_t rb = clamp_12(byte_val >> 4)    # Upper 4 bits
        cdef uint32_t lx = clamp_4_max0(skip_index - 1)
        
        cdef uint64_t vx
        cdef bytes offset_slice
        cdef uint32_t raw_offset
        if lx > 0:
            offset_slice = zeta_slice[1:1+lx]
            raw_offset = int.from_bytes(offset_slice, "little")
            vx = int(program_counter) + z(raw_offset, lx)
        else:
            vx = int(program_counter)
        
        # Return in unified format: (vx, vy, ra, rb, rd)
        return (vx, 0, ra, rb, 0)

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = branch_eq_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[170] = _e
_e = CyTableEntry(); _e.fn = branch_ne_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[171] = _e
_e = CyTableEntry(); _e.fn = branch_lt_u_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[172] = _e
_e = CyTableEntry(); _e.fn = branch_lt_s_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[173] = _e
_e = CyTableEntry(); _e.fn = branch_ge_u_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[174] = _e
_e = CyTableEntry(); _e.fn = branch_ge_s_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[175] = _e
