# cython: language_level=3
from ..common.types import Accessibility as CommonAccessibility
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

    # Low-level page management
    cdef unsigned char* _get_cpage(self, uint32_t page_idx, bint create=*)
    cdef void _clear_bitsets(self) noexcept
    cpdef void _sync_bitsets_from_sets(self)
    
    # C-level byte operations
    cdef void _set_byte_c(self, uint32_t addr, uint8_t value) noexcept
    cdef uint8_t _get_byte_c(self, uint32_t addr) noexcept
    
    # C-level access control
    cdef bint _has_access_c(self, uint32_t page_idx, int mode) noexcept nogil
    cdef void _set_access_c(self, uint32_t page_idx, int mode, bint value) noexcept nogil
    cdef void _set_access_range_c(self, uint32_t start_page, uint32_t num_pages, int mode, bint value) noexcept nogil
    cdef void _check_access_c(self, uint32_t start_page, uint32_t num_pages, int mode, uint32_t fault_addr)
    cdef void _alter_accessibility_c(self, uint32_t start_addr, uint32_t length, uint8_t access)

    # C-level memory operations
    cdef void _zero_memory_range_c(self, uint32_t start_page, uint32_t num_pages) noexcept
    cdef bint _is_accessible_c(self, uint32_t address, uint32_t length, int access) noexcept

    # Python-accessible wrappers
    cpdef _set_byte(self, uint32_t addr, uint8_t value)
    cpdef int _get_byte(self, uint32_t addr)
    cpdef bytes read(self, uint32_t address, int length)
    cpdef void write(self, uint32_t address, data)

cdef uint32_t _norm(uint32_t addr) noexcept
cdef uint32_t _get_start_page(uint32_t addr) noexcept  
cdef uint32_t _get_page_offset(uint32_t addr) noexcept
cdef void _get_page_range(uint32_t start_addr, uint32_t length, uint32_t *start_page, uint32_t *num_pages) noexcept