# cython: language_level=3

"""
Cython declaration file for cy_program.pyx

This file exposes the CyProgram class and its methods for efficient
Cython-to-Cython calls and inheritance.
"""

from libc.stdint cimport int32_t, uint32_t, uint8_t

cdef class CyProgram:
    """
    Cython-optimized INT_Program with fast skip cache and basic block operations.
    """
    
    # Public attributes
    cdef public int32_t            z
    cdef public list               jump_table
    cdef public bytes              instruction_set
    cdef public list               offset_bitmask
    cdef public list               basic_blocks
    cdef public int32_t            instruction_set_len
    cdef public int32_t            jump_table_len
    cdef public list               _extended_bitmask
    cdef public uint8_t*           zeta
    cdef public int32_t            zeta_len
    cdef public set                _basic_blocks_set
    cdef public dict               _exec_blocks
    
    # Private/internal attributes
    cdef int32_t*                  _skip_cache
    cdef public int32_t            _skip_cache_len
    
    # Internal methods
    cdef _precompute_cache(self)
    cdef int32_t encode_size(self)
    cdef int32_t encode_into(self, bytearray buffer, int32_t offset)
    
    # Public methods that can be called from other Cython modules
    cdef uint32_t branch(self, int32_t counter, int32_t branch, bint cond)
    cdef uint32_t skip(self, int32_t pc) nogil
    cdef uint32_t djump(self, uint32_t counter, uint32_t a)