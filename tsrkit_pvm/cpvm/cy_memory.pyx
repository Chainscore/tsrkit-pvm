# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False

"""
Hardcore C-level memory model for the CPVM.

• Uses raw C buffers for pages with PyMem_Malloc/Free
• C-level bitsets for ultra-fast page permission checks
• All hot paths run in pure C with nogil
• Maximum performance optimized for block processing
"""

from libc.stdint cimport uint32_t, uint8_t, uint64_t, uintptr_t
from libc.string cimport memset, memcpy
from libc.stdlib cimport malloc, free
from cpython.mem cimport PyMem_Malloc, PyMem_Free
from .cy_memory cimport Accessibility, ACC_READ, ACC_WRITE, ACC_NONE
from .cy_status cimport PAGE_FAULT, PvmExit, PVM_PAGE_FAULT
from .cy_utils cimport get_pages, total_page_size, total_zone_size
from ..common.types import Accessibility as CommonAccessibility

DEF PVM_ADDR_ALIGNMENT = 2
DEF PVM_INIT_DATA_SIZE = 2**24
DEF PVM_INIT_ZONE_SIZE = 2**16
DEF PAGE_SIZE = 4096  # PAGE_SIZE = 2**12
DEF MAX_PAGES = 1048576  # 1M pages for 4GB address space


cdef inline uint32_t _norm(uint32_t addr) noexcept:
    """Wrap address into 32-bit space."""
    return addr & 0xFFFF_FFFF

cdef inline uint32_t _get_start_page(uint32_t addr) noexcept:
    """Get page index for address."""
    return addr >> 12  # addr // PAGE_SIZE

cdef inline uint32_t _get_page_offset(uint32_t addr) noexcept:
    """Get offset within page."""
    return addr & 0xFFF  # addr % PAGE_SIZE

cdef inline void _get_page_range(uint32_t start_addr, uint32_t length, 
                                uint32_t *start_page, uint32_t *num_pages) noexcept:
    """Calculate page range for address range."""
    start_page[0] = start_addr >> 12
    cdef uint32_t end_addr = start_addr + length - 1
    cdef uint32_t end_page = end_addr >> 12
    num_pages[0] = end_page - start_page[0] + 1


cdef class CyMemory:
    """
    Ultra-high performance page-oriented memory:
    
    • Raw C buffers per page (PyMem_Malloc'd 4KB chunks)
    • C-level bitsets for lightning-fast access control  
    • All hot paths run in pure C with nogil
    • Zero Python object overhead in memory operations
    """

    # ───────────────────────── low-level page helpers ──────────────────────
    cdef unsigned char* _get_cpage(self, uint32_t page_idx, bint create=False):
        """
        Return raw C pointer for page `page_idx`.
        If `create` is true, allocate the page (filled with 0) when absent.
        """
        cdef Py_ssize_t ptr_val
        cdef unsigned char* buf

        ptr_val = self._pages.get(page_idx, 0)
        if ptr_val == 0:
            if not create:
                return <unsigned char*>0
            buf = <unsigned char*>PyMem_Malloc(PAGE_SIZE)
            if buf == NULL:
                raise MemoryError()
            memset(buf, 0, PAGE_SIZE)
            self._pages[page_idx] = <Py_ssize_t>buf
            return buf
        return <unsigned char*>ptr_val

    # ---------------------------------------------------------------- init --
    def __init__(self,
                 dict      data                = None,
                 list[int] allowed_read_pages  = None,
                 list[int] allowed_write_pages = None,
                 int  heap                = 0):
        # NOTE: _pages now maps page-idx → Py_ssize_t (raw pointer)
        self._pages     = {}
        self._r_pages   = set(allowed_read_pages or [])
        self._w_pages   = set(allowed_write_pages or [])
        self.heap_break = heap

        # Initialize C-level bitsets to zero
        self._clear_bitsets()

        # Set initial permissions in bitsets
        self._sync_bitsets_from_sets()

        if data:
            for addr, val in data.items():
                self._set_byte_c(addr, val)

    def __dealloc__(self):
        """Free every allocated raw page."""
        cdef Py_ssize_t ptr_val
        for ptr_val in self._pages.values():
            PyMem_Free(<void*>ptr_val)

    cdef void _clear_bitsets(self) noexcept:
        """Clear all C-level bitsets."""
        cdef int i
        for i in range(16384):  # MAX_PAGES / 64
            self._r_bitset[i] = 0
            self._w_bitset[i] = 0

    cpdef void _sync_bitsets_from_sets(self):
        """Synchronize C-level bitsets from Python sets."""
        # Clear all bitsets first
        self._clear_bitsets()
        
        # Set read permissions
        cdef int pg
        for pg in self._r_pages:
            self._set_access_c(pg, ACC_READ, True)
        
        # Set write permissions
        for pg in self._w_pages:
            self._set_access_c(pg, ACC_WRITE, True)

    # ───────────────────── C-level bitset access control ───────────────────
    cdef bint _has_access_c(self, uint32_t page_idx, int mode) noexcept nogil:
        """Check if page has access permission using C-level bitsets."""
        if page_idx >= MAX_PAGES:
            return False
        
        cdef uint32_t word_idx = page_idx >> 6  # divide by 64
        cdef uint32_t bit_idx = page_idx & 63   # modulo 64
        cdef uint64_t mask = <uint64_t>1 << bit_idx
        
        if mode == ACC_WRITE:
            return (self._w_bitset[word_idx] & mask) != 0
        else:  # ACC_READ
            return ((self._r_bitset[word_idx] | self._w_bitset[word_idx]) & mask) != 0

    cdef void _set_access_c(self, uint32_t page_idx, int mode, bint value) noexcept nogil:
        """Set page access permission using C-level bitsets."""
        if page_idx >= MAX_PAGES:
            return
            
        cdef uint32_t word_idx = page_idx >> 6  # divide by 64
        cdef uint32_t bit_idx = page_idx & 63   # modulo 64
        cdef uint64_t mask = <uint64_t>1 << bit_idx
        
        if mode == ACC_WRITE:
            if value:
                self._w_bitset[word_idx] |= mask
            else:
                self._w_bitset[word_idx] &= ~mask
        elif mode == ACC_READ:
            if value:
                self._r_bitset[word_idx] |= mask
            else:
                self._r_bitset[word_idx] &= ~mask

    cdef void _set_access_range_c(self, uint32_t start_page, uint32_t num_pages, int mode, bint value) noexcept nogil:
        """Set access permission for a range of pages using C-level bitsets."""
        cdef uint32_t i
        for i in range(num_pages):
            self._set_access_c(start_page + i, mode, value)

    cdef void _check_access_c(self, uint32_t start_page, uint32_t num_pages, int mode, uint32_t fault_addr):
        """Fast C-level access checking using bitsets."""
        cdef uint32_t i
        for i in range(num_pages):
            if not self._has_access_c(start_page + i, mode):
                raise PvmExit(2, fault_addr)

    cdef void _alter_accessibility_c(self, uint32_t start_addr, uint32_t length, uint8_t access):
        """Ultra-fast C-level accessibility alteration."""
        cdef uint32_t start_page, num_pages
        _get_page_range(start_addr, length, &start_page, &num_pages)
        
        # Update bitsets directly
        if access == ACC_WRITE:
            self._set_access_range_c(start_page, num_pages, ACC_WRITE, True)
            self._set_access_range_c(start_page, num_pages, ACC_READ, False)
        elif access == ACC_READ:
            self._set_access_range_c(start_page, num_pages, ACC_READ, True)
            self._set_access_range_c(start_page, num_pages, ACC_WRITE, False)
        else:  # NONE
            self._set_access_range_c(start_page, num_pages, ACC_READ, False)
            self._set_access_range_c(start_page, num_pages, ACC_WRITE, False)

    # ───────────────────── single-byte helpers (C-level) ───────────────────
    cdef void _set_byte_c(self, uint32_t addr, uint8_t value) noexcept:
        cdef uint32_t pg = _get_start_page(addr)
        cdef uint32_t off = _get_page_offset(addr)
        (<unsigned char*>self._get_cpage(pg, True))[off] = value

    cdef uint8_t _get_byte_c(self, uint32_t addr) noexcept:
        cdef uint32_t pg = _get_start_page(addr)
        cdef uint32_t off = _get_page_offset(addr)
        cdef unsigned char* buf = self._get_cpage(pg, False)
        if buf == NULL:
            return 0
        return buf[off]

    cdef void _zero_memory_range_c(self, uint32_t start_page, uint32_t num_pages) noexcept:
        """Zero a range of pages using C-level operations."""
        if num_pages <= 0:
            return
        cdef uint32_t pg
        cdef unsigned char* buf
        for pg in range(start_page, start_page + num_pages):
            buf = self._get_cpage(pg, True)
            memset(buf, 0, PAGE_SIZE)

    cdef bint _is_accessible_c(self, uint32_t address, uint32_t length, int access) noexcept:
        """Fast C-level accessibility check."""
        if length <= 0:
            return True
        
        cdef uint32_t start_page, num_pages
        _get_page_range(address, length, &start_page, &num_pages)
        
        cdef uint32_t i
        for i in range(num_pages):
            if not self._has_access_c(start_page + i, access):
                return False
        return True

    # Python-level wrappers (keep minimal for external API) -----------------
    cpdef _set_byte(self, uint32_t addr, uint8_t value):
        self._set_byte_c(addr, value)

    cpdef int _get_byte(self, uint32_t addr):
        return self._get_byte_c(addr)

    # ---------------------------------------------------------------- read --
    cpdef bytes read(self, uint32_t address, int length):
        if length <= 0:
            return b""
        address = _norm(address)
        
        # Fast C-level access check using bitsets
        cdef uint32_t start_page, num_pages
        _get_page_range(address, length, &start_page, &num_pages)
        self._check_access_c(start_page, num_pages, ACC_READ, address)

        cdef bytearray out = bytearray(length)
        cdef unsigned char[:] out_mv = out

        cdef uint32_t cur = address
        cdef int copied = 0
        cdef int remaining = length
        cdef uint32_t pg, off, chunk_size
        cdef unsigned char* src

        # Ultra-fast C-level memory copying
        while remaining > 0:
            pg = _get_start_page(cur)
            off = _get_page_offset(cur)
            chunk_size = PAGE_SIZE - off
            if chunk_size > remaining:
                chunk_size = remaining

            src = self._get_cpage(pg, False)
            if src != NULL:
                memcpy(&out_mv[copied], src + off, chunk_size)
            else:
                memset(&out_mv[copied], 0, chunk_size)

            copied += chunk_size
            remaining -= chunk_size
            cur += chunk_size

        return bytes(out)

    # ---------------------------------------------------------------- write --
    cpdef void write(self, uint32_t address, data):
        if not data:
            return
        address = _norm(address)
        cdef const unsigned char[:] in_mv = data
        cdef int length = in_mv.shape[0]

        # Fast C-level access check using bitsets
        cdef uint32_t start_page, num_pages
        _get_page_range(address, length, &start_page, &num_pages)
        self._check_access_c(start_page, num_pages, ACC_WRITE, address)

        cdef uint32_t cur = address
        cdef int copied = 0
        cdef int remaining = length
        cdef uint32_t pg, off, chunk
        cdef unsigned char* dst

        while remaining:
            pg = _get_start_page(cur)
            off = _get_page_offset(cur)
            chunk = PAGE_SIZE - off
            if chunk > remaining:
                chunk = remaining

            dst = self._get_cpage(pg, True)
            memcpy(dst + off, &in_mv[copied], chunk)

            copied    += chunk
            remaining -= chunk
            cur       += chunk

    # -------------------------------------------------------- misc helpers --
    def is_accessible(self, address, length, access = CommonAccessibility.READ):
        """Python wrapper for accessibility check."""
        return self._is_accessible_c(address, length, access.value)

    def alter_accessibility(self, start, len_, access):
        self._alter_accessibility_c(start, len_, access.value)

    def zero_memory_range(self, int start_page, int num_pages):
        """Python wrapper for memory zeroing."""
        self._zero_memory_range_c(start_page, num_pages)

    # ----------------------------------------------------------- from_pc --
    @classmethod
    def from_pc(cls, bytes read, bytes write, bytes args,
                int z, int s, uint32_t heap=0):
        """
        Build memory from program counters.  Parameters mirror the interpreter
        version; implementation matches logic but uses the new internals.
        """
        cdef uint32_t last_page
        mem = cls(data={}, allowed_read_pages=[], allowed_write_pages=[], heap=heap)
        
        # read zone
        read_start = PVM_INIT_ZONE_SIZE
        for i, b in enumerate(read):
            mem._set_byte(read_start + i, b)
        mem._r_pages.update(get_pages(read_start, total_page_size(len(read))))

        # write zone
        write_start = 2 * PVM_INIT_ZONE_SIZE + total_zone_size(len(read))
        for i, b in enumerate(write):
            mem._set_byte(write_start + i, b)
        w_pages = get_pages(
            write_start,
            total_page_size(len(write)) + (z * PAGE_SIZE),
        )
        mem._w_pages.update(w_pages)

        # heap
        if len(w_pages) > 0:
            mem.heap_break = (w_pages[len(w_pages) - 1] + 1) * PAGE_SIZE

        # stack
        stack_start = 2**32 - 2 * PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE - total_page_size(s)
        mem._w_pages.update(get_pages(stack_start, total_page_size(s)))

        # args zone
        arg_start = 2**32 - PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE
        for i, b in enumerate(args):
            mem._set_byte(arg_start + i, b)
        mem._r_pages.update(get_pages(arg_start, total_page_size(len(args))))

        # IMPORTANT: Sync C-level bitsets after updating Python sets
        mem._sync_bitsets_from_sets()
        
        return mem

    # --------------------------------------------------------- dunder --
    def __repr__(self):
        return f"CyMemory(pages={len(self._pages)}, heap={self.heap_break})"

    def __eq__(self, other):
        if not isinstance(other, CyMemory):
            return NotImplemented
        return (
            self._pages == other._pages and
            self._r_pages == other._r_pages and
            self._w_pages == other._w_pages
        )
