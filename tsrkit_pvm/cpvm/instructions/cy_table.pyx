# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

"""
Unified Cython interface implementation for all instruction tables.
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t, int32_t
from ..cy_program cimport CyProgram
from ..cy_memory cimport CyMemory
from .cy_table cimport CyTable, CyTableEntry, instr_fn_t, InstructionProps

cdef class CyTable:
    """
    Base class implementation for all instruction tables.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Default implementation returns zeros for all arguments.
        Subclasses should override this to extract actual arguments.
        Returns: InstructionProps struct
        """
        cdef InstructionProps props
        props.vx = 0
        props.vy = 0
        props.ra = 0
        props.rb = 0
        props.rd = 0
        return props

# Provide an empty implementation body for CyTableEntry
cdef class CyTableEntry:
    pass