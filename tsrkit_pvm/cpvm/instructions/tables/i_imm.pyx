# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

"""
Cython optimized i_imm instruction table.
Instructions with 1 immediate argument (opcodes 10-19).
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from ...cy_status cimport HOST
from ...cy_utils cimport chi, clamp_4
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

cdef tuple ecalli_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """
    OPC10: Ecalli - Execute call immediate.
    Performs a host call with the immediate value.
    
    Args:
        program: Current program state
        registers: Current register state
        memory: Current memory state  
        counter: Current program counter
        vx: Immediate value to pass to host
        vy, ra, rb, rd: Unused for this instruction
        
    Returns:
        Tuple of (execution_status, next_pc)
    """
    # Call HOST with the immediate value (vx) and return status with next_pc
    return (HOST(vx), <uint32_t>0xFFFFFFFF)

cdef class CyInstructionsWArgs1Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 immediate argument.
    """
    
    cpdef tuple get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract immediate value from program bytes.
        Returns (vx, vy, ra, rb, rc) where vx is the immediate value, others are 0.
        """
        cdef uint32_t lx = clamp_4(<uint8_t>skip_index)
        cdef uint32_t start = program_counter + 1
        cdef uint32_t end = start + lx
        
        # Extract bytes and convert to integer
        cdef bytes byte_slice = program.zeta[start:end]
        cdef uint64_t immediate_value = int.from_bytes(byte_slice, "little")
        
        # Apply chi transformation
        cdef uint64_t vx = <uint64_t>chi(<uint64_t>immediate_value, <uint8_t>lx)
        
        # Return in unified format: (vx, vy, ra, rb, rd)
        return (vx, 0, 0, 0, 0)

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = ecalli_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[10] = _e

