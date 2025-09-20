# cython: language_level=3

"""
Cython header file for i_imm instruction table.
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from ..cy_table cimport CyTable, InstructionProps
from ...cy_program cimport CyProgram

cdef class CyInstructionsWArgs1Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 immediate argument.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index)
    
    cpdef dict get_table(self)# Table declaration
cdef dict TABLE