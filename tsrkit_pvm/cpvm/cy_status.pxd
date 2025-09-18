# cython: language_level=3
"""
Simple Cython status definitions for PVM.
"""

from libc.stdint cimport int32_t, uint64_t

# Fixed-size registers array - 13 registers as per PVM spec
ctypedef uint64_t registers_t[13]

# Simple C enum for status codes
cdef enum PvmStatus:
    PVM_HALT = 0
    PVM_PANIC = 1  
    PVM_PAGE_FAULT = 2
    PVM_HOST = 3
    PVM_OUT_OF_GAS = 4
    PVM_CONTINUE = 5

# Simple struct for status with optional register
cdef struct StatusValue:
    int32_t code
    int32_t register  # -1 if not used

# Simple error class
cdef class PvmError(Exception):
    cdef public int32_t code
    cdef public int32_t register
    cdef public str message