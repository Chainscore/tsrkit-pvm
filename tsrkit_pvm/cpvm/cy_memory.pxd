# cython: language_level=3

from libc.stdint cimport uint32_t, uint8_t, uint64_t

cdef enum Accessibility:
    ACC_READ
    ACC_WRITE
    ACC_NONE

READ = ACC_READ
WRITE = ACC_WRITE
NONE = ACC_NONE

# Maximum number of pages for 4GB address space (2^32 / 2^12 = 2^20 = 1M pages)
DEF MAX_PAGES = 1048576  # 1M pages

cdef class CyMemory:
    cdef public dict _pages                    # page_idx -> Py_ssize_t (raw pointer) 
    cdef public set _r_pages                   # readable pages (keeping for compatibility)
    cdef public set _w_pages                   # writable pages (keeping for compatibility)
    cdef uint64_t _r_bitset[16384]            # C-level read permission bitset (1M bits / 64 = 16384)
    cdef uint64_t _w_bitset[16384]            # C-level write permission bitset
    cdef public int heap_break

    cdef unsigned char* _get_cpage(self, uint32_t page_idx, bint create=*)
    cdef void _set_byte_c(self, uint32_t addr, uint8_t value)
    cdef uint8_t _get_byte_c(self, uint32_t addr)
    cdef void _check_access_c(self, uint32_t start_page, uint32_t num_pages, int mode, uint32_t fault_addr)
    cdef bint _has_access_c(self, uint32_t page_idx, int mode) nogil
    cdef void _set_access_c(self, uint32_t page_idx, int mode, bint value) nogil

    cpdef _set_byte(self, uint32_t addr, uint8_t value)
    cpdef int _get_byte(self, uint32_t addr)

    cpdef bytes read(self, uint32_t address, int length)
    cpdef void write(self, uint32_t address, data)

cdef uint32_t _norm(uint32_t addr) noexcept