# cython: language_level=3

"""
Compact, bounds-checked memory model for the CPVM.

• Stores actual bytes in a densely packed Python bytearray (per page) instead
  of one huge array / dict.
• Uses two Python sets (read/write) for fast page-level access checks.
• All addresses are 32-bit unsigned; they are normalised with a cheap mask.
"""

from libc.stdint cimport uint32_t, uint8_t, uint64_t
from libc.string cimport memset
# ---------------------------------------------------------------------------
# Local accessibility enum – avoids importing Python-only symbol
# ---------------------------------------------------------------------------

from tsrkit_pvm.common.utils import get_pages, total_page_size, total_zone_size
from tsrkit_pvm.common.constants import (
    PVM_INIT_DATA_SIZE,
    PVM_INIT_ZONE_SIZE,
    PVM_MEMORY_PAGE_SIZE,
)
from tsrkit_pvm.common.status import PAGE_FAULT, PvmError

cdef inline uint32_t _norm(uint32_t addr) noexcept:
    """Wrap address into 32-bit space."""
    return addr & 0xFFFF_FFFF


cdef class CyMemory:
    """
    Page-oriented memory:

    • `self._pages`   : dict[int, bytearray]   — page-index → 4 KiB bytes
    • `self._r_pages` : set[int]               — readable pages
    • `self._w_pages` : set[int]               — writable pages
    """

    # ---------------------------------------------------------------- init --
    def __init__(
        self,
        dict      data                = None,
        list[int] allowed_read_pages  = None,
        list[int] allowed_write_pages = None,
        int  heap                = 0,
    ):
        self._pages     = {}
        self._r_pages   = set(allowed_read_pages or [])
        self._w_pages   = set(allowed_write_pages or [])
        self.heap_break = heap

        if data:
            for addr, val in data.items():
                self._set_byte(<uint32_t>addr, <uint8_t>val)

    # ------------------------------------------------------------ internals --
    cdef inline bytearray _get_page(self, uint32_t page_idx, bint create=False):
        """Return bytearray for `page_idx`; optionally create an empty page."""
        cdef bytearray pg
        pg = self._pages.get(page_idx)
        if pg is None:
            if not create:
                return None
            pg = bytearray(PVM_MEMORY_PAGE_SIZE)
            self._pages[page_idx] = pg
        return pg

    # ─────────────────────────────────────────────────────────────────────────────
    # Internal helpers (cdef) and thin Python-visible wrappers (cpdef)
    # ─────────────────────────────────────────────────────────────────────────────
    cdef inline void _set_byte_c(CyMemory self, uint32_t addr, uint8_t value):
        """Low-level byte store – no access checks."""
        cdef uint32_t page_idx = addr // PVM_MEMORY_PAGE_SIZE
        cdef uint32_t offset   = addr %  PVM_MEMORY_PAGE_SIZE
        self._get_page(page_idx, True)[offset] = value

    cdef inline uint8_t _get_byte_c(CyMemory self, uint32_t addr):
        """Low-level byte load – no access checks."""
        cdef uint32_t page_idx = addr // PVM_MEMORY_PAGE_SIZE
        cdef uint32_t offset   = addr %  PVM_MEMORY_PAGE_SIZE
        cdef bytearray pg = self._get_page(page_idx, False)
        if pg is None:
            return 0
        return pg[offset]

    # Python-level wrappers -------------------------------------------------
    cpdef _set_byte(self, uint32_t addr, uint8_t value):
        self._set_byte_c(addr, value)       # call the *bound* cdef helper

    cpdef int _get_byte(self, uint32_t addr):
        return self._get_byte_c(addr)       # call the *bound* cdef helper

    cdef inline void _check_access(self, list pages, int mode, uint32_t fault_addr):
        """Raise PAGE_FAULT if any page in `pages` is not accessible in `mode`."""
        cdef int pg
        if mode == ACC_WRITE:
            for pg in pages:
                if pg not in self._w_pages:
                    raise PvmError(PAGE_FAULT(fault_addr))
        else:                              # READ
            for pg in pages:
                if pg not in self._r_pages and pg not in self._w_pages:
                    raise PvmError(PAGE_FAULT(fault_addr))

    # ---------------------------------------------------------------- read --
    def read(self, uint32_t address, int length) -> bytes:
        if length <= 0:
            return b""
        address = _norm(address)
        pages = get_pages(address, length)
        self._check_access(pages, ACC_READ, address)

        cdef bytearray out = bytearray(length)
        cdef int i
        cdef uint32_t addr = address
        for i in range(length):
            out[i] = self._get_byte_c(addr)
            addr += 1             # 32-bit wrap is now well-defined
        return bytes(out)

    # ---------------------------------------------------------------- write --
    def write(self, uint32_t address, data):
        if not data:
            return
        address = _norm(address)
        length  = len(data)
        pages = get_pages(address, length)
        self._check_access(pages, ACC_WRITE, address)

        cdef int i
        cdef uint8_t val
        cdef uint32_t addr = address
        for i in range(length):
            val = data[i] if isinstance(data, (bytes, bytearray)) else data[i] & 0xFF
            self._set_byte_c(addr, val)
            addr += 1

    # -------------------------------------------------------- misc helpers --
    def is_accessible(self, uint32_t address, uint32_t length, int access = ACC_READ):
        if length <= 0:
            return True
        pages = get_pages(address, length)
        try:
            self._check_access(pages, access, address)
            return True
        except PvmError:
            return False

    def alter_accessibility(self, uint32_t start, uint32_t len_, int access):
        pages = get_pages(start, len_)
        if access == ACC_WRITE:
            self._w_pages.update(pages)
            self._r_pages.difference_update(pages)
        elif access == ACC_READ:
            self._r_pages.update(pages)
            self._w_pages.difference_update(pages)
        else:  # NONE
            self._r_pages.difference_update(pages)
            self._w_pages.difference_update(pages)

    def zero_memory_range(self, int start_page, int num_pages):
        if num_pages <= 0:
            return
        cdef int pg
        for pg in range(start_page, start_page + num_pages):
            self._pages[pg] = bytearray(PVM_MEMORY_PAGE_SIZE)  # replace

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
            total_page_size(len(write)) + (z * PVM_MEMORY_PAGE_SIZE),
        )
        mem._w_pages.update(w_pages)

        # heap
        if len(w_pages) > 0:
            mem.heap_break = (w_pages[len(w_pages) - 1] + 1) * PVM_MEMORY_PAGE_SIZE

        # stack
        stack_start = 2**32 - 2 * PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE - total_page_size(s)
        mem._w_pages.update(get_pages(stack_start, total_page_size(s)))

        # args zone
        arg_start = 2**32 - PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE
        for i, b in enumerate(args):
            mem._set_byte(arg_start + i, b)
        mem._r_pages.update(get_pages(arg_start, total_page_size(len(args))))

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
