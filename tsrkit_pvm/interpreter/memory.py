from __future__ import annotations
from typing import Dict, List, Self, Sequence, TYPE_CHECKING
from tsrkit_pvm.common.types import Accessibility
from tsrkit_pvm.common.utils import get_pages, total_page_size, total_zone_size
from tsrkit_pvm.common.constants import (
    PVM_INIT_DATA_SIZE,
    PVM_INIT_ZONE_SIZE,
    PVM_MEMORY_PAGE_SIZE,
)
from tsrkit_pvm.common.status import PAGE_FAULT, ExecutionStatus, PvmError

ADDR_MOD = 2**32
PAGE_SIZE = PVM_MEMORY_PAGE_SIZE
LOW_BOUND = 0

# Pre-computed constants for optimization
_PAGE_SHIFT = 12  # log2(PAGE_SIZE) = log2(4096) = 12
_PAGE_MASK = PAGE_SIZE - 1  # 4095 for fast modulo
_ADDR_MASK = ADDR_MOD - 1  # For fast address normalization

# Pre-allocated zero page for reads from unallocated memory
_ZERO_PAGE = bytes(PAGE_SIZE)


class INT_Memory:
    """
    Sparse, page-mapped memory model with read/write page protection.
    Uses hybrid approach with optimized sets and bit manipulation.
    """
    __slots__ = ('_pages', '_r_pages', '_w_pages', 'heap_break', 'logger', '_page_cache')

    def __init__(
        self,
        data: Dict[int, int] | None = None,
        allowed_read_pages: List[int] | None = None,
        allowed_write_pages: List[int] | None = None,
        heap: int = 0,
        logger=None,
    ):
        allowed_read_pages = allowed_read_pages or []
        allowed_write_pages = allowed_write_pages or []
        
        # Use optimized set implementation for better performance than bitsets for sparse access
        self._r_pages: set[int] = set(allowed_read_pages)
        self._w_pages: set[int] = set(allowed_write_pages)
        
        self.logger = logger

        # Sparse page map with pre-allocation strategy
        self._pages: Dict[int, bytearray] = {}
        
        # Simple cache for frequently accessed pages  
        self._page_cache: Dict[int, bytearray] = {}
        
        if data:
            # Bulk-load initial bytes more efficiently
            sorted_addrs = sorted(data.items())
            current_page = -1
            page_data = None
            
            for addr, val in sorted_addrs:
                if not (0 <= val <= 255):
                    raise ValueError(f"Memory: invalid value {val} @ {addr}")
                
                page_idx = addr >> _PAGE_SHIFT
                if page_idx != current_page:
                    current_page = page_idx
                    page_data = self._page_for(addr, create=True)
                
                page_data[addr & _PAGE_MASK] = val

        self.heap_break: int = heap

    # --------------------------------------------------------------------- #
    # Core helpers - Optimized with bit manipulation
    # --------------------------------------------------------------------- #

    @staticmethod
    def _page_index(addr: int) -> int:
        """Fast page index calculation using bit shift instead of division."""
        return addr >> _PAGE_SHIFT

    def _page_for(self, addr: int, *, create: bool = False) -> bytearray:
        """
        Get the underlying page buffer for an address with caching.
        Creates a fresh zero-filled page if `create` is True.
        """
        pg = addr >> _PAGE_SHIFT
        
        # Check cache first for hot pages
        cached_page = self._page_cache.get(pg)
        if cached_page is not None:
            return cached_page
        
        # Check main storage
        page_data = self._pages.get(pg)
        if page_data is not None:
            # Cache this page for future access
            if len(self._page_cache) < 16:  # Limit cache size
                self._page_cache[pg] = page_data
            return page_data
        
        if not create:
            # Return read-only zero page (shared) to avoid dict hits
            return _ZERO_PAGE
            
        # Create new page
        ba = bytearray(PAGE_SIZE)
        self._pages[pg] = ba
        # Cache new page
        if len(self._page_cache) < 16:
            self._page_cache[pg] = ba
        return ba

    def _assert_access(self, addr: int, *, write: bool = False) -> None:
        """Optimized access check."""
        if addr < LOW_BOUND:
            raise Exception(f"Memory panic: address {addr} < {LOW_BOUND}")
        
        pg = addr >> _PAGE_SHIFT
        
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

    # --------------------------------------------------------------------- #
    # Public operations - Optimized for performance
    # --------------------------------------------------------------------- #

    def read(self, address: int, length: int) -> bytes:
        if length <= 0:
            return b""
        
        # Fast address normalization using bitwise AND
        address = address & _ADDR_MASK
        end = address + length

        # Fast path for single-page reads (most common case)
        if (address >> _PAGE_SHIFT) == ((end - 1) >> _PAGE_SHIFT):
            pg = address >> _PAGE_SHIFT
            # Inline permission check for speed
            if pg not in self._r_pages and pg not in self._w_pages:
                if self.logger:
                    self.logger.debug(f"Not allowed to read {address}(Page={pg})")
                raise PvmError(PAGE_FAULT(address))
            
            # Fast single-page read
            page_off = address & _PAGE_MASK
            src_page = self._page_cache.get(pg) or self._pages.get(pg) or _ZERO_PAGE
            if src_page is not _ZERO_PAGE and len(self._page_cache) < 16 and pg not in self._page_cache:
                self._page_cache[pg] = src_page
            return bytes(src_page[page_off : page_off + length])

        # Multi-page path (less common)
        out = bytearray(length)
        out_mv = memoryview(out)
        cursor = 0
        
        while address < end:
            pg = address >> _PAGE_SHIFT
            page_off = address & _PAGE_MASK
            chunk = min(PAGE_SIZE - page_off, end - address)

            # Inline permission check for speed
            if pg not in self._r_pages and pg not in self._w_pages:
                if self.logger:
                    self.logger.debug(f"Not allowed to read {address}(Page={pg})")
                raise PvmError(PAGE_FAULT(address))
            
            # Fast page lookup with caching
            src_page = self._page_cache.get(pg)
            if src_page is None:
                src_page = self._pages.get(pg) or _ZERO_PAGE
                if src_page is not _ZERO_PAGE and len(self._page_cache) < 16:
                    self._page_cache[pg] = src_page
            
            # Fast memory copy
            out_mv[cursor : cursor + chunk] = src_page[page_off : page_off + chunk]

            address += chunk
            cursor += chunk
        return bytes(out)

    def write(self, address: int, data_bytes: bytes | Sequence[int]) -> None:
        if not data_bytes:
            return
            
        # Fast address normalization
        address = address & _ADDR_MASK
        length = len(data_bytes)
        end = address + length

        # Fast path for single-page writes (most common case)
        if (address >> _PAGE_SHIFT) == ((end - 1) >> _PAGE_SHIFT):
            pg = address >> _PAGE_SHIFT
            # Inline permission check for speed
            if pg not in self._w_pages:
                if self.logger:
                    self.logger.debug(f"Not allowed to write {address}(Page={pg})")
                raise PvmError(PAGE_FAULT(address))
            
            # Fast single-page write
            page_off = address & _PAGE_MASK
            dst_page = self._page_cache.get(pg)
            if dst_page is None:
                dst_page = self._pages.get(pg)
                if dst_page is None:
                    dst_page = bytearray(PAGE_SIZE)
                    self._pages[pg] = dst_page
                if len(self._page_cache) < 16:
                    self._page_cache[pg] = dst_page
            
            dst_page[page_off : page_off + length] = data_bytes
            return

        # Multi-page path (less common)
        in_mv = memoryview(data_bytes)
        cursor = 0
        
        while address < end:
            pg = address >> _PAGE_SHIFT
            page_off = address & _PAGE_MASK
            chunk = min(PAGE_SIZE - page_off, end - address)

            # Inline permission check for speed
            if pg not in self._w_pages:
                if self.logger:
                    self.logger.debug(f"Not allowed to write {address}(Page={pg})")
                raise PvmError(PAGE_FAULT(address))
            
            # Fast page lookup/creation with caching
            dst_page = self._page_cache.get(pg)
            if dst_page is None:
                dst_page = self._pages.get(pg)
                if dst_page is None:
                    dst_page = bytearray(PAGE_SIZE)
                    self._pages[pg] = dst_page
                if len(self._page_cache) < 16:
                    self._page_cache[pg] = dst_page
            
            # Fast memory copy
            dst_page[page_off : page_off + chunk] = in_mv[cursor : cursor + chunk]

            address += chunk
            cursor += chunk

    def get_pages(self, address: int, length: int) -> list[int]:
        """Get list of page numbers spanning a memory range."""
        return get_pages(address, length)

    def is_accessible(self, address: int, length: int, access: Accessibility = Accessibility.READ) -> bool:
        """Optimized accessibility check."""
        if length <= 0:
            return True
            
        pages = self.get_pages(address, length)
        if access == Accessibility.WRITE:
            return all(pg in self._w_pages for pg in pages)
        elif access == Accessibility.READ:
            return all(pg in self._r_pages or pg in self._w_pages for pg in pages)
        return True

    def dump_memory(self, start: int, end: int):  # debug helper
        """Debug helper - optimized version."""
        result = []
        for addr in range(start, end):
            pg = addr >> _PAGE_SHIFT
            if pg in self._pages:
                result.append(self._pages[pg][addr & _PAGE_MASK])
            else:
                result.append(0)
        return result

    # repr / equality keep old behaviour for debugging or tests  
    def __repr__(self):
        # Simplified repr to avoid expensive calculations during logging
        return f"Memory(pages={len(self._pages)}, heap={self.heap_break})"

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
            
        # Compare permission sets
        if self._r_pages != other._r_pages or self._w_pages != other._w_pages:
            return False
            
        # Compare only the cells both memories have explicitly written
        for pg, buf in self._pages.items():
            other_buf = other._pages.get(pg)
            if other_buf and buf != other_buf:
                return False
        for pg, buf in other._pages.items():
            self_buf = self._pages.get(pg)
            if self_buf and buf != self_buf:
                return False
        return True

    @classmethod
    def from_pc(cls, read: bytes, write: bytes, args: bytes, z: int, s: int) -> Self:
        memory = {}

        read_start = PVM_INIT_ZONE_SIZE
        read_pages = get_pages(read_start, total_page_size(len(read)))
        # print(f"READ \t\t | Start: {int(read_start).to_bytes(4).hex()} \t | End {int(read_pages[-1] * PVM_MEMORY_PAGE_SIZE).to_bytes(4).hex()}")
        for i, byt in enumerate(read):
            memory[read_start + i] = int(byt)

        write_start = 2 * PVM_INIT_ZONE_SIZE + total_zone_size(len(read))
        write_pages = get_pages(
            write_start,
            total_page_size(len(write)) + (int(z) * PVM_MEMORY_PAGE_SIZE),
        )
        # print(f"WRITE \t\t | Start: {int(write_start).to_bytes(4).hex()} \t | End {int((write_pages[-1] + 1) * PVM_MEMORY_PAGE_SIZE).to_bytes(4).hex()}")
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
        # print(f"ARG \t\t | START: {int(arg_start).to_bytes(4).hex()}")
        for i, byt in enumerate(args):
            memory[arg_start + i] = int(byt)

        return cls(memory, read_pages, write_pages, heap=heap)

    def zero_memory_range(self, start_page: int, num_pages: int):
        """Optimized memory zeroing."""
        if num_pages <= 0:
            return
            
        for page_idx in range(start_page, start_page + num_pages):
            # Create or get existing page
            page_data = self._page_for(page_idx * PAGE_SIZE, create=True)
            # Fast zero fill
            page_data[:] = b'\x00' * PAGE_SIZE

    def alter_accessibility(self, start: int, len_: int, access: Accessibility):
        """Optimized accessibility alteration."""
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

_ZERO_PAGE = bytes(PAGE_SIZE)

# Export INT_Memory as Memory for backward compatibility
Memory = INT_Memory
