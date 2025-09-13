# cython: boundscheck=False, wraparound=False, nonecheck=False, cdivision=True, language_level=3
# cython: profile=False, embedsignature=True

"""
Cython optimized memory implementation for PVM.

This provides a high-performance implementation of the sparse, page-mapped memory model
with read/write page protection, optimized with Cython for C-level performance.
"""

cimport cython
from libc.stdint cimport int32_t, int64_t, uint32_t, uint64_t, uint8_t
from libc.stdlib cimport malloc, free, calloc
from libc.string cimport memcpy, memset
from cpython.dict cimport PyDict_GetItem, PyDict_SetItem, PyDict_DelItem
from cpython.set cimport PySet_Contains, PySet_Add, PySet_Discard
from cpython.bytes cimport PyBytes_FromStringAndSize, PyBytes_AsString
from cpython.bytearray cimport PyByteArray_FromStringAndSize, PyByteArray_AsString, PyByteArray_GET_SIZE

from typing import Dict, List, Sequence, Optional, Union, Any
from typing_extensions import Self
from tsrkit_pvm.common.types import Accessibility
from tsrkit_pvm.common.utils import get_pages, total_page_size, total_zone_size
from tsrkit_pvm.common.constants import (
    PVM_INIT_DATA_SIZE,
    PVM_INIT_ZONE_SIZE,
    PVM_MEMORY_PAGE_SIZE,
)
from tsrkit_pvm.common.status import PAGE_FAULT, ExecutionStatus, PvmError

# Constants
cdef uint32_t ADDR_MOD = 2**32
cdef uint32_t PAGE_SIZE = PVM_MEMORY_PAGE_SIZE
cdef uint32_t LOW_BOUND = 0

# Pre-computed constants for optimization
cdef uint32_t _PAGE_SHIFT = 12  # log2(PAGE_SIZE) = log2(4096) = 12
cdef uint32_t _PAGE_MASK = PAGE_SIZE - 1  # 4095 for fast modulo
cdef uint32_t _ADDR_MASK = ADDR_MOD - 1  # For fast address normalization

# Cache size limit
cdef uint32_t _CACHE_LIMIT = 16

cdef class CyMemory:
    """
    Cython optimized sparse, page-mapped memory model with read/write page protection.
    
    This class provides the same interface as INT_Memory but with Cython optimizations
    for critical memory operations.
    """
    
    # Use C data structures for better performance
    cdef dict _pages          # Dict[int, bytearray] - page storage
    cdef set _r_pages         # Set[int] - readable pages
    cdef set _w_pages         # Set[int] - writable pages
    cdef dict _page_cache     # Dict[int, bytearray] - page cache
    cdef uint64_t heap_break  # Heap break pointer
    cdef object logger        # Logger object
    cdef bytes _zero_page     # Shared zero page for reads
    
    def __cinit__(self):
        """Initialize C-level data structures."""
        self._pages = {}
        self._r_pages = set()
        self._w_pages = set()
        self._page_cache = {}
        self.heap_break = 0
        self.logger = None
        # Create a shared zero page
        self._zero_page = bytes(PAGE_SIZE)
    
    def __init__(
        self,
        data: Dict[int, int] = None,
        allowed_read_pages: List[int] = None,
        allowed_write_pages: List[int] = None,
        heap: int = 0,
        logger: Optional[Any] = None,
    ):
        """Initialize the memory system with optional initial data and permissions."""
        if allowed_read_pages is None:
            allowed_read_pages = []
        if allowed_write_pages is None:
            allowed_write_pages = []
        
        # Initialize permission sets
        self._r_pages = set(allowed_read_pages)
        self._w_pages = set(allowed_write_pages)
        self.logger = logger
        self.heap_break = heap
        
        if data:
            self._bulk_load_data(data)
    
    cdef void _bulk_load_data(self, dict data):
        """Efficiently bulk-load initial data."""
        cdef int addr, val, page_idx, page_off
        cdef int current_page = -1
        cdef bytearray page_data = None
        
        # Sort addresses for better cache locality
        sorted_addrs = sorted(data.items())
        
        for addr, val in sorted_addrs:
            if not (0 <= val <= 255):
                raise ValueError(f"Memory: invalid value {val} @ {addr}")
            
            page_idx = addr >> _PAGE_SHIFT
            if page_idx != current_page:
                current_page = page_idx
                page_data = self._page_for_create(addr)
            
            page_off = addr & _PAGE_MASK
            page_data[page_off] = val
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef inline uint32_t _page_index(self, uint64_t addr) nogil:
        """Fast page index calculation using bit shift."""
        return <uint32_t>(addr >> _PAGE_SHIFT)
    
    cdef bytearray _page_for_create(self, uint64_t addr):
        """Get or create a page for writing at the given address."""
        cdef uint32_t pg = self._page_index(addr)
        
        # Check cache first
        page_data = self._page_cache.get(pg)
        if page_data is not None:
            return page_data
        
        # Check main storage
        page_data = self._pages.get(pg)
        if page_data is not None:
            # Cache this page if cache isn't full
            if len(self._page_cache) < _CACHE_LIMIT:
                self._page_cache[pg] = page_data
            return page_data
        
        # Create new page
        page_data = bytearray(PAGE_SIZE)
        self._pages[pg] = page_data
        
        # Cache new page if cache isn't full
        if len(self._page_cache) < _CACHE_LIMIT:
            self._page_cache[pg] = page_data
        
        return page_data
    
    cdef object _page_for_read(self, uint64_t addr):
        """Get a page for reading (returns zero page if not allocated)."""
        cdef uint32_t pg = self._page_index(addr)
        
        # Check cache first
        page_data = self._page_cache.get(pg)
        if page_data is not None:
            return page_data
        
        # Check main storage
        page_data = self._pages.get(pg)
        if page_data is not None:
            # Cache this page if cache isn't full
            if len(self._page_cache) < _CACHE_LIMIT:
                self._page_cache[pg] = page_data
            return page_data
        
        # Return shared zero page
        return self._zero_page
    
    @cython.boundscheck(False)
    cdef inline void _assert_access(self, uint64_t addr, bint write) except *:
        """Optimized access permission check."""
        if addr < LOW_BOUND:
            raise Exception(f"Memory panic: address {addr} < {LOW_BOUND}")
        
        cdef uint32_t pg = self._page_index(addr)
        
        if write:
            if pg not in self._w_pages:
                if self.logger:
                    self.logger.debug(f"Not allowed to write {addr}(Page={pg})")
                raise PvmError(PAGE_FAULT(addr))
        else:
            if pg not in self._r_pages and pg not in self._w_pages:
                if self.logger:
                    self.logger.debug(f"Not allowed to read {addr}(Page={pg})")
                raise PvmError(PAGE_FAULT(addr))
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    def read(self, uint64_t address, uint32_t length):
        """
        High-performance memory read operation.
        
        Args:
            address: Memory address to read from
            length: Number of bytes to read
            
        Returns:
            list: The read data as a list of integers (for compatibility)
        """
        cdef uint64_t end
        cdef uint32_t start_page, end_page, page_off
        cdef object src_page
        
        if length == 0:
            return []
        
        # Fast address normalization
        address = address & _ADDR_MASK
        end = address + length
        
        # Fast path for single-page reads (most common case)
        start_page = self._page_index(address)
        end_page = self._page_index(end - 1)
        
        if start_page == end_page:
            # Inline permission check for speed
            if start_page not in self._r_pages and start_page not in self._w_pages:
                if self.logger:
                    self.logger.debug(f"Not allowed to read {address}(Page={start_page})")
                raise PvmError(PAGE_FAULT(address))
            
            # Fast single-page read
            page_off = address & _PAGE_MASK
            src_page = self._page_for_read(address)
            
            if isinstance(src_page, bytearray):
                return list(src_page[page_off:page_off + length])
            else:
                # Zero page case
                return [0] * length
        
        # Multi-page path
        return self._read_multipage(address, length, end)
    
    cdef list _read_multipage(self, uint64_t address, uint32_t length, uint64_t end):
        """Handle multi-page reads."""
        cdef list out = []
        cdef uint32_t pg, page_off, chunk
        cdef object page_data
        
        while address < end:
            pg = self._page_index(address)
            page_off = address & _PAGE_MASK
            chunk = min(PAGE_SIZE - page_off, end - address)
            
            # Permission check
            if pg not in self._r_pages and pg not in self._w_pages:
                if self.logger:
                    self.logger.debug(f"Not allowed to read {address}(Page={pg})")
                raise PvmError(PAGE_FAULT(address))
            
            # Get page data
            page_data = self._page_for_read(address)
            
            # Copy data
            if isinstance(page_data, bytearray):
                out.extend(list(page_data[page_off:page_off + chunk]))
            else:
                # Zero page - add zeros
                out.extend([0] * chunk)
            
            address += chunk
            
        return out
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    def write(self, uint64_t address, data_bytes):
        """
        High-performance memory write operation.
        
        Args:
            address: Memory address to write to
            data_bytes: Data to write (bytes or sequence of ints)
        """
        cdef uint32_t length, start_page, end_page, page_off
        cdef uint64_t end
        cdef bytearray dst_page
        
        if not data_bytes:
            return
        
        # Fast address normalization
        address = address & _ADDR_MASK
        length = len(data_bytes)
        end = address + length
        
        # Fast path for single-page writes (most common case)
        start_page = self._page_index(address)
        end_page = self._page_index(end - 1)
        
        if start_page == end_page:
            # Inline permission check for speed
            if start_page not in self._w_pages:
                if self.logger:
                    self.logger.debug(f"Not allowed to write {address}(Page={start_page})")
                raise PvmError(PAGE_FAULT(address))
            
            # Fast single-page write
            page_off = address & _PAGE_MASK
            dst_page = self._page_for_create(address)
            dst_page[page_off:page_off + length] = data_bytes
            return
        
        # Multi-page path
        self._write_multipage(address, data_bytes, length, end)
    
    cdef void _write_multipage(self, uint64_t address, object data_bytes, uint32_t length, uint64_t end):
        """Handle multi-page writes."""
        cdef uint32_t cursor = 0
        cdef uint32_t pg, page_off, chunk
        cdef bytearray dst_page
        
        # Convert to memoryview for efficient slicing
        if isinstance(data_bytes, bytes):
            in_mv = memoryview(data_bytes)
        else:
            # Convert sequence of ints to bytes
            in_mv = memoryview(bytes(data_bytes))
        
        while address < end:
            pg = self._page_index(address)
            page_off = address & _PAGE_MASK
            chunk = min(PAGE_SIZE - page_off, end - address)
            
            # Permission check
            if pg not in self._w_pages:
                if self.logger:
                    self.logger.debug(f"Not allowed to write {address}(Page={pg})")
                raise PvmError(PAGE_FAULT(address))
            
            # Get or create page
            dst_page = self._page_for_create(address)
            
            # Copy data
            dst_page[page_off:page_off + chunk] = in_mv[cursor:cursor + chunk]
            
            address += chunk
            cursor += chunk
    
    def get_pages(self, address: int, length: int) -> list[int]:
        """Get list of page numbers spanning a memory range."""
        return get_pages(address, length)
    
    def is_accessible(self, address: int, length: int, access: Accessibility = Accessibility.READ) -> bool:
        """Check if a memory range is accessible with the given access type."""
        if length <= 0:
            return True
        
        pages = self.get_pages(address, length)
        if access == Accessibility.WRITE:
            return all(pg in self._w_pages for pg in pages)
        elif access == Accessibility.READ:
            return all(pg in self._r_pages or pg in self._w_pages for pg in pages)
        return True
    
    def zero_memory_range(self, start_page: int, num_pages: int) -> None:
        """Zero out a range of memory pages."""
        cdef int page_idx
        cdef bytearray page_data
        
        if num_pages <= 0:
            return
        
        for page_idx in range(start_page, start_page + num_pages):
            # Create or get existing page
            page_data = self._page_for_create(page_idx * PAGE_SIZE)
            # Fast zero fill
            page_data[:] = b'\x00' * PAGE_SIZE
    
    def alter_accessibility(self, start: int, len_: int, access: Accessibility) -> None:
        """Change the accessibility of a memory range."""
        pages = get_pages(start, len_)
        
        for pg in pages:
            if access == Accessibility.WRITE:
                self._w_pages.add(pg)
                self._r_pages.discard(pg)
            elif access == Accessibility.READ:
                self._r_pages.add(pg)
                self._w_pages.discard(pg)
            else:
                self._r_pages.discard(pg)
                self._w_pages.discard(pg)
        
        # Invalidate cache for affected pages
        for pg in pages:
            self._page_cache.pop(pg, None)
    
    @classmethod
    def from_pc(cls, read: bytes, write: bytes, args: bytes, z: int, s: int):
        """Create memory instance from program counter data."""
        memory = {}

        read_start = PVM_INIT_ZONE_SIZE
        read_pages = get_pages(read_start, total_page_size(len(read)))
        for i, byt in enumerate(read):
            memory[read_start + i] = int(byt)

        write_start = 2 * PVM_INIT_ZONE_SIZE + total_zone_size(len(read))
        write_pages = get_pages(
            write_start,
            total_page_size(len(write)) + (int(z) * PVM_MEMORY_PAGE_SIZE),
        )
        for i, byt in enumerate(write):
            memory[write_start + i] = int(byt)

        heap = int((write_pages[-1] + 1) * PVM_MEMORY_PAGE_SIZE)

        write_pages.extend(
            get_pages(
                2**32
                - 2 * PVM_INIT_ZONE_SIZE
                - PVM_INIT_DATA_SIZE
                - total_page_size(s),
                total_page_size(s),
            )
        )

        arg_start = 2**32 - PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE
        read_pages.extend(get_pages(arg_start, total_page_size(len(args))))
        for i, byt in enumerate(args):
            memory[arg_start + i] = int(byt)

        return cls(memory, read_pages, write_pages, heap=heap)
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"CyMemory(pages={len(self._pages)}, heap={self.heap_break})"
    
    def __eq__(self, other: object) -> bool:
        """Equality comparison with another memory instance."""
        if not isinstance(other, CyMemory):
            return NotImplemented
        
        # Compare permission sets
        if self._r_pages != other._r_pages or self._w_pages != other._w_pages:
            return False
        
        # Compare page contents
        for pg, buf in self._pages.items():
            other_buf = other._pages.get(pg)
            if other_buf and buf != other_buf:
                return False
        for pg, buf in other._pages.items():
            self_buf = self._pages.get(pg)
            if self_buf and buf != self_buf:
                return False
        return True

# Provide alias for backward compatibility
CyINT_Memory = CyMemory
