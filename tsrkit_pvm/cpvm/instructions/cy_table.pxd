# cython: language_level=3

"""
Unified Cython interface for all instruction tables.
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t, int32_t
from ..cy_program cimport CyProgram
from ..cy_memory cimport CyMemory

# C struct for instruction properties - eliminates Python tuple overhead
cdef struct InstructionProps:
    uint64_t vx
    uint64_t vy
    uint8_t ra
    uint8_t rb
    uint8_t rd

# Define the unified instruction function pointer type
# Returns tuple of (execution_status, next_pc)
ctypedef uint32_t (*instr_fn_t)(
    CyProgram program,
    uint64_t *registers,
    CyMemory memory,
    uint32_t counter,
    uint64_t vx,
    uint64_t vy,
    uint8_t ra,
    uint8_t rb, 
    uint8_t rd
)

# Define the table entry as a Python-visible Cython class, so it
# can be stored in Python dicts and carried around easily.
cdef class CyTableEntry:
    cdef instr_fn_t fn
    cdef public uint32_t gas_cost
    cdef public bint is_terminating

cdef class CyTable:
    """
    Base class for all instruction tables.
    Provides unified interface for instruction argument extraction.
    """
    
    # Unified argument extraction - returns InstructionProps C struct
    # All tables must implement this to provide arguments in standard format
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index)