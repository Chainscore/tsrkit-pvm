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
from tsrkit_pvm.common.status import HOST
from tsrkit_pvm.common.utils import chi, clamp_4
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

# Separate dispatch function for ecalli instruction
cdef int ecalli_fn(uint64_t *registers, CyMemory memory, uint64_t vx, uint64_t vy, 
                   uint8_t ra, uint8_t rb, uint8_t rc):
    """
    OPC10: Ecalli - Execute call immediate.
    Performs a host call with the immediate value.
    
    Args:
        registers: Current register state
        memory: Current memory state  
        vx: Immediate value to pass to host
        vy, ra, rb, rc: Unused for this instruction
        
    Returns:
        HOST status code
    """
    # Call HOST with the immediate value (vx)
    return HOST(vx)

cdef class CyInstructionsWArgs1Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 immediate argument.
    """
    
    @staticmethod
    cdef tuple get_props(uint32_t program_counter, CyProgram program):
        """
        Extract immediate value from program bytes.
        Returns (vx, vy, ra, rb, rc) where vx is the immediate value, others are 0.
        """
        # Get skip index from program
        cdef uint32_t skip_index = program.skip(program_counter)
        cdef uint32_t lx = clamp_4(skip_index)
        cdef uint32_t start = program_counter + 1
        cdef uint32_t end = start + lx
        
        # Extract bytes and convert to integer
        cdef bytes byte_slice = program.zeta[start:end]
        cdef uint64_t immediate_value = int.from_bytes(byte_slice, "little")
        
        # Apply chi transformation
        cdef uint64_t vx = chi(immediate_value, lx)
        
        # Return in unified format: (vx, vy, ra, rb, rc)
        return (vx, 0, 0, 0, 0)
    
    @staticmethod
    cdef dict get_table():
        """Return the instruction table mapping opcodes to their handlers."""
        cdef dict table = {}
        cdef CyTableEntry entry
        
        # OPC10: ecalli
        entry.fn = ecalli_fn
        entry.gas_cost = 1
        entry.is_terminating = False
        table[10] = entry
        
        return table

