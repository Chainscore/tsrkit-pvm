# cython: language_level=3
# cython: boundscheck=False, wraparound=False, nonecheck=False, cdivision=True

"""
Simple Cython status implementation for PVM.
"""

cimport cython
from libc.stdint cimport int32_t
from .cy_status cimport PvmStatus, StatusValue, PvmError

cdef class PvmError(Exception):
    """Simple PVM error with status code."""
    
    def __cinit__(self, int32_t code, int32_t register=-1, str message=""):
        self.code = code
        self.register = register 
        self.message = message
        super().__init__(f"PVM Error {code}: {message}")

# Helper functions to create status values
cdef inline StatusValue make_status(int32_t code, int32_t register=-1):
    cdef StatusValue status
    status.code = code
    status.register = register
    return status

# Status constants as functions for easy use
def HALT():
    return make_status(PVM_HALT)

def PANIC():
    return make_status(PVM_PANIC)

def PAGE_FAULT(int32_t register):
    return make_status(PVM_PAGE_FAULT, register)

def HOST(int32_t register):
    return make_status(PVM_HOST, register)

def OUT_OF_GAS():
    return make_status(PVM_OUT_OF_GAS)

CONTINUE = make_status(PVM_CONTINUE)