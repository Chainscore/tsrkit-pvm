# cython: language_level=3

from libc.stdint cimport int32_t, uint8_t, uint32_t, uint64_t


cdef enum PvmStatus:
    PVM_HALT = 0
    PVM_PANIC = 1  
    PVM_PAGE_FAULT = 2
    PVM_HOST = 3
    PVM_OUT_OF_GAS = 4
    PVM_CONTINUE = 5


cdef class CyStatus:
    cdef public uint8_t code     
    cdef public uint32_t register
    
    cdef void set_values(self, uint8_t code, uint32_t register)

# Status constants declarations for external use
cdef CyStatus CONTINUE
cdef CyStatus HALT
cdef CyStatus PANIC  
cdef CyStatus OUT_OF_GAS
cdef CyStatus PAGE_FAULT(uint32_t register)
cdef CyStatus HOST(uint32_t register)


cdef class PvmExit(Exception):
    cdef public uint32_t code
    cdef public uint32_t register
    cdef public uint32_t next_pc
    cdef public uint32_t gas_cost
    cdef public str message