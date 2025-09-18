# cython: language_level=3

"""
Cython header file for i_reg_i_ewimm instruction table.
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from ..cy_table cimport CyTable
from ...cy_program cimport CyProgram

cdef class CyInstructionsWArgs1Reg1EwImm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 register + 1 EwImm argument.
    """
    
    cpdef tuple get_props(self, uint32_t program_counter, CyProgram program)
    
    cpdef dict get_table(self)

# Table declaration
cdef dict TABLE