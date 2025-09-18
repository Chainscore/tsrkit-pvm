# cython: language_level=3

"""
Unified Cython interface for all instruction tables.
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t, int32_t
from ..cy_program cimport CyProgram
from ..cy_memory cimport CyMemory

# Define the unified instruction function pointer type
ctypedef int (*instr_fn_t)(uint64_t *registers,
                           CyMemory memory,
                           uint64_t vx,
                           uint64_t vy,
                           uint8_t ra,
                           uint8_t rb, 
                           uint8_t rc)

# Define the table entry structure
ctypedef struct CyTableEntry:
    instr_fn_t fn
    uint32_t gas_cost
    bint is_terminating

cdef class CyTable:
    """
    Base class for all instruction tables.
    Provides unified interface for instruction argument extraction and table access.
    """
    
    # Unified argument extraction - returns (vx, vy, ra, rb, rc)
    # All tables must implement this to provide arguments in standard format
    @staticmethod
    cdef tuple get_props(uint32_t program_counter, CyProgram program)
    
    # Table access - returns mapping of opcode -> CyTableEntry
    # Each table must implement this class method
    @staticmethod
    cdef dict get_table()