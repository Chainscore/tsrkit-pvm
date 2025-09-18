# cython: language_level=3

from libc.stdint cimport uint32_t, uint8_t

cdef enum Accessibility:
    ACC_READ
    ACC_WRITE
    ACC_NONE

cdef class CyMemory:
    cdef public dict _pages
    cdef public set _r_pages
    cdef public set _w_pages
    cdef public int heap_break

    cdef inline bytearray _get_page(self, uint32_t page_idx, bint create=*)
    cdef inline void _set_byte_c(CyMemory self, uint32_t addr, uint8_t value)
    cdef inline uint8_t _get_byte_c(CyMemory self, uint32_t addr)
    cdef inline void _check_access(self, list pages, int mode, uint32_t fault_addr)

    cpdef _set_byte(self, uint32_t addr, uint8_t value)
    cpdef int _get_byte(self, uint32_t addr)

cdef inline uint32_t _norm(uint32_t addr) noexcept