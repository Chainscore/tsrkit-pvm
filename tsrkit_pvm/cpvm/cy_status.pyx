# cython: language_level=3
# cython: boundscheck=False, wraparound=False, nonecheck=False, cdivision=True
cimport cython
from libc.stdint cimport int32_t, uint8_t, uint32_t
from .cy_status cimport CyStatus

cdef class CyStatus:
    cdef void set_values(self, uint8_t code, uint32_t register):
        self.code = code
        self.register = register

cdef CyStatus CONTINUE = CyStatus()
CONTINUE.set_values(PVM_CONTINUE, 0)

cdef CyStatus HALT = CyStatus()
HALT.set_values(PVM_HALT, 0)

cdef CyStatus PANIC = CyStatus()
PANIC.set_values(PVM_PANIC, 0)

cdef CyStatus OUT_OF_GAS = CyStatus()
OUT_OF_GAS.set_values(PVM_OUT_OF_GAS, 0)

cdef CyStatus HOST(uint32_t register):
    """Create HOST status with register value."""
    cdef CyStatus status = CyStatus()
    status.code = PVM_HOST
    status.register = register
    return status

cdef CyStatus PAGE_FAULT(uint32_t register):
    """Create PAGE_FAULT status with register value."""
    cdef CyStatus status = CyStatus()
    status.code = PVM_PAGE_FAULT
    status.register = register
    return status

cdef class PvmError(Exception):
    def __cinit__(self, int32_t code, int32_t register=-1, str message=""):
        self.code = code
        self.register = register 
        self.message = message
        super().__init__(f"PVM Error {code}: {message}")