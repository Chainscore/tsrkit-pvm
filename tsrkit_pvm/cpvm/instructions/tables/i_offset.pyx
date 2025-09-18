# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

"""
Cython optimized i_offset instruction table.
Instructions with 1 offset argument (opcode 40).
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import clamp_4, z
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

# Unified dispatch function for jump instruction
cdef tuple jump_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """
    OPC40: Unconditional jump to specified offset.
    
    Args:
        program: Current program state
        registers: Register array 
        memory: Memory object
        counter: Current program counter
        vx: Target jump address
        vy, ra, rb, rd: Unused for this instruction
    
    Returns:
        Tuple of (status, next_pc)
    """
    # Use the program's branch method for proper jump validation
    cdef object status_result = program.branch(counter, vx, True)
    cdef object status = status_result[0]
    cdef uint32_t target_counter = status_result[1]
    
    if status == CONTINUE and target_counter != counter:
        return (status, target_counter)
    
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef class CyWArgsOneOffset(CyTable):
    """
    Cython optimized instruction table for instructions with 1 offset argument.
    """
    
    cpdef tuple get_props(self, uint32_t program_counter, CyProgram program):
        """
        Extract offset value from program bytes.
        Returns (vx, vy, ra, rb, rd) where vx is the computed offset, others are 0.
        """
        # Get skip index from program
        cdef uint32_t skip_index = program.skip(program_counter)
        cdef uint32_t lx = clamp_4(skip_index)
        cdef uint32_t start = program_counter + 1
        cdef uint32_t end = start + lx
        
        # Extract bytes and convert to integer
        cdef bytes offset_bytes = program.zeta[start:end]
        cdef uint32_t raw_offset = int.from_bytes(offset_bytes, "little")
        cdef uint64_t vx = int(program_counter) + z(raw_offset, lx)
        
        # Return in unified format: (vx, vy, ra, rb, rd)
        return (vx, 0, 0, 0, 0)

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = jump_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[40] = _e

