# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 1 register + 1 immediate + 1 offset argument instructions.

This table handles instructions that take one register, one immediate, and one offset argument:
- load_imm_jump: Load immediate and jump
- branch_eq_imm/ne_imm: Branch if register equals/not equals immediate
"""

cimport cython
from libc.stdint cimport uint32_t, uint64_t, int64_t, uint8_t

from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import chi, z, clamp_12, clamp_4, clamp_4_max0, compare
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram



cdef tuple load_imm_jump_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC80: Load immediate value into register and jump to offset."""
    registers[ra] = vx
    status_result = program.branch(counter, vy, True)
    status = status_result[0]
    target_counter = status_result[1]
    if status == CONTINUE and target_counter != counter:
        return status, target_counter
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_eq_imm_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC81: Branch if register equals immediate."""
    cdef bint condition = registers[ra] == vx
    status_result = program.branch(counter, vy, condition)
    status = status_result[0]
    target_counter = status_result[1]
    if status == CONTINUE and target_counter != counter:
        return status, target_counter
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_ne_imm_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC82: Branch if register not equals immediate."""
    cdef bint condition = registers[ra] != vx
    status_result = program.branch(counter, vy, condition)
    status = status_result[0]
    target_counter = status_result[1]
    if status == CONTINUE and target_counter != counter:
        return status, target_counter
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_lt_u_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC83: Branch if register less than immediate (unsigned)."""
    cdef bint condition = registers[ra] < vx
    status_result = program.branch(counter, vy, condition)
    status = status_result[0]
    counter = status_result[1]
    if status == CONTINUE and counter != counter:
        return status, counter
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_le_u_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC84: Branch if register less than or equal immediate (unsigned)."""
    cdef bint condition = registers[ra] <= vx
    status_result = program.branch(counter, vy, condition)
    status = status_result[0]
    counter = status_result[1]
    if status == CONTINUE and counter != counter:
        return status, counter
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_ge_u_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC85: Branch if register greater than or equal immediate (unsigned)."""
    cdef bint condition = registers[ra] >= vx
    status_result = program.branch(counter, vy, condition)
    status = status_result[0]
    counter = status_result[1]
    if status == CONTINUE and counter != counter:
        return status, counter
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_gt_u_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC86: Branch if register greater than immediate (unsigned)."""
    cdef bint condition = registers[ra] > vx
    status_result = program.branch(counter, vy, condition)
    status = status_result[0]
    counter = status_result[1]
    if status == CONTINUE and counter != counter:
        return status, counter
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_lt_s_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC87: Branch if register less than immediate (signed)."""
    cdef bint condition = <int64_t>registers[ra] < <int64_t>vx
    status_result = program.branch(counter, vy, condition)
    status = status_result[0]
    counter = status_result[1]
    if status == CONTINUE and counter != counter:
        return status, counter
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_le_s_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC88: Branch if register less than or equal immediate (signed)."""
    cdef bint condition = <int64_t>registers[ra] <= <int64_t>vx
    status_result = program.branch(counter, vy, condition)
    status = status_result[0]
    counter = status_result[1]
    if status == CONTINUE and counter != counter:
        return status, counter
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_ge_s_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC89: Branch if register greater than or equal immediate (signed)."""
    cdef bint condition = <int64_t>registers[ra] >= <int64_t>vx
    status_result = program.branch(counter, vy, condition)
    status = status_result[0]
    counter = status_result[1]
    if status == CONTINUE and counter != counter:
        return status, counter
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef tuple branch_gt_s_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC90: Branch if register greater than immediate (signed)."""
    cdef bint condition = <int64_t>registers[ra] > <int64_t>vx
    status_result = program.branch(counter, vy, condition)
    status = status_result[0]
    counter = status_result[1]
    if status == CONTINUE and counter != counter:
        return status, counter
    return CONTINUE, <uint32_t>0xFFFFFFFF


cdef class InstructionsWArgs1Reg1Imm1Offset(CyTable):
    """
    Cython optimized instruction table for instructions with 1 register + 1 immediate + 1 offset argument.
    """
    
    cpdef tuple get_props(self, uint32_t program_counter, CyProgram program):
        """
        Extract register, immediate, and offset arguments from program bytes.
        Returns (vx, vy, ra, rb, rd) where vx is immediate, vy is offset, ra is register, others are 0.
        """
        cdef uint32_t skip_index = program.skip(program_counter)
        cdef bytes zeta_slice = program.zeta[program_counter + 1:program_counter + 8]
        cdef uint32_t byte_val = zeta_slice[0]
        
        cdef uint8_t ra = clamp_12(byte_val & 0x0F)           # Lower 4 bits
        cdef uint32_t lx = clamp_4((byte_val >> 4) & 0x07)     # Next 3 bits
        cdef uint32_t ly = clamp_4_max0(int(skip_index) - lx - 1)
        
        cdef uint64_t vx = 0
        cdef bytes imm1_slice
        if lx > 0:
            imm1_slice = zeta_slice[1:1+lx]
            vx = chi(int.from_bytes(imm1_slice, "little"), lx)
        
        cdef uint64_t vy = int(program_counter)
        cdef bytes imm2_slice
        if ly > 0:
            imm2_slice = zeta_slice[1+lx:1+lx+ly]
            vy = int(program_counter) + z(int.from_bytes(imm2_slice, "little"), ly)
        
        # Return in unified format: (vx, vy, ra, rb, rd)
        return (vx, vy, ra, 0, 0)


    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = load_imm_jump_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[80] = _e
_e = CyTableEntry(); _e.fn = branch_eq_imm_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[81] = _e
_e = CyTableEntry(); _e.fn = branch_ne_imm_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[82] = _e
