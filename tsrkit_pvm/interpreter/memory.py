from __future__ import annotations
from typing import Dict, List, Sequence, TYPE_CHECKING, Optional, Union, Any
from typing_extensions import Self
from bitarray import bitarray
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

MAX_PAGES = 1 << 20  # 1M pages for 4GB address space


class INT_Memory:
    """
    Sparse, page-mapped memory model with read/write page protection.
    Optimized with hot page caching for sequential access patterns.
    """
    __slots__ = ('_pages', '_r_pages', '_w_pages', 'heap_break', 'logger',
                 '_hot_page_num', '_hot_page_data', '_hot_page_writable')

    def __init__(
        self,
        data: Dict[int, int] | None = None,
        allowed_read_pages: List[int] | None = None,
        allowed_write_pages: List[int] | None = None,
        heap: int = 0,
        logger: Optional[Any] = None,
    ):
        allowed_read_pages = allowed_read_pages or []
        allowed_write_pages = allowed_write_pages or []
        
        # Use bitarray for efficient permission tracking
        self._r_pages: bitarray = bitarray(MAX_PAGES)
        self._r_pages.setall(0)
        self._w_pages: bitarray = bitarray(MAX_PAGES)
        self._w_pages.setall(0)
        
        # Set initial permissions
        for pg in allowed_read_pages:
            if pg < MAX_PAGES:
                self._r_pages[pg] = 1
        for pg in allowed_write_pages:
            if pg < MAX_PAGES:
                self._w_pages[pg] = 1
        
        self.logger = logger

        # Sparse page map with pre-allocation strategy
        self._pages: Dict[int, bytearray] = {}
        
        # Hot page optimization - avoid dictionary lookups for sequential access
        self._hot_page_num: int = -1
        self._hot_page_data: Optional[bytearray] = None
        self._hot_page_writable: bool = False
        
        if data:
            # Simple bulk loading
            self._bulk_load_sparse(sorted(data.items()))

        self.heap_break: int = heap

    def _bulk_load_sparse(self, sorted_addrs: List[tuple[int, int]]) -> None:
        """Traditional sparse loading for non-contiguous data."""
        current_page = -1
        page_data: Optional[bytearray] = None
        
        for addr, val in sorted_addrs:
            if not (0 <= val <= 255):
                raise ValueError(f"Memory: invalid value {val} @ {addr}")
                
            page_idx = addr >> _PAGE_SHIFT
            if page_idx != current_page:
                current_page = page_idx
                page_data = self._pages.get(page_idx)
                if page_data is None:
                    page_data = bytearray(PAGE_SIZE)
                    self._pages[page_idx] = page_data
            
            assert page_data is not None 
            page_data[addr & _PAGE_MASK] = val

    # --------------------------------------------------------------------- #
    # Core helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _page_index(addr: int) -> int:
        """Fast page index calculation using bit shift instead of division."""
        return addr >> _PAGE_SHIFT

    def _page_for(self, addr: int, *, create: bool = False) -> Union[bytearray, bytes]:
        """
        Get the underlying page buffer for an address.
        Creates a fresh zero-filled page if `create` is True.
        """
        pg = addr >> _PAGE_SHIFT
        
        # Check main storage
        page_data = self._pages.get(pg)
        if page_data is not None:
            return page_data
        
        if not create:
            # Return read-only zero page (shared) to avoid dict hits
            return _ZERO_PAGE
            
        # Create new page
        ba = bytearray(PAGE_SIZE)
        self._pages[pg] = ba
        return ba

    def _assert_access(self, addr: int, *, write: bool = False) -> None:
        """Optimized access check with bitarray."""
        if addr < LOW_BOUND:
            raise Exception(f"Memory panic: address {addr} < {LOW_BOUND}")
        
        pg = addr >> _PAGE_SHIFT
        if pg >= MAX_PAGES:
            raise PvmError(PAGE_FAULT(addr))
        
        if write:
            if not self._w_pages[pg]:
                if self.logger:
                    self.logger.debug(f"Not allowed to write {addr}(Page={pg})")
                raise PvmError(PAGE_FAULT(addr))
        else:
            if not (self._r_pages[pg] or self._w_pages[pg]):
                if self.logger:
                    self.logger.debug(f"Not allowed to read {addr}(Page={pg})")
                raise PvmError(PAGE_FAULT(addr))

    # --------------------------------------------------------------------- #
    # Public operations
    # --------------------------------------------------------------------- #

    def read(self, address: int, length: int) -> bytes:
        if length <= 0:
            return b""
        
        address = address & _ADDR_MASK
        
        # Ultra-fast path: single page, hot cache hit
        pg = address >> _PAGE_SHIFT
        if pg == self._hot_page_num and self._hot_page_data is not None:
            page_off = address & _PAGE_MASK
            if page_off + length <= PAGE_SIZE:
                return bytes(self._hot_page_data[page_off:page_off + length])
        
        # Single page path (most common)
        if (address >> _PAGE_SHIFT) == ((address + length - 1) >> _PAGE_SHIFT):
            if pg >= MAX_PAGES or not (self._r_pages[pg] or self._w_pages[pg]):
                raise PvmError(PAGE_FAULT(address))
            
            page_off = address & _PAGE_MASK
            page_data = self._pages.get(pg)
            
            if page_data is None:
                # Zero data - avoid allocation
                return b'\x00' * length
            
            # Update hot cache
            self._hot_page_num = pg
            self._hot_page_data = page_data
            self._hot_page_writable = bool(self._w_pages[pg])
            
            return bytes(page_data[page_off:page_off + length])
        
        # Multi-page fallback (rare)
        return self._read_multipage(address, length)
    
    def _read_multipage(self, address: int, length: int) -> bytes:
        """Separate multi-page read to keep main path fast."""
        result = bytearray(length)
        end = address + length
        cursor = 0
        
        while address < end:
            pg = address >> _PAGE_SHIFT
            if pg >= MAX_PAGES or not (self._r_pages[pg] or self._w_pages[pg]):
                raise PvmError(PAGE_FAULT(address))
            
            page_off = address & _PAGE_MASK
            chunk = min(PAGE_SIZE - page_off, end - address)
            
            page_data = self._pages.get(pg)
            if page_data is None:
                # Leave result as zeros (already initialized)
                pass
            else:
                result[cursor:cursor + chunk] = page_data[page_off:page_off + chunk]
            
            cursor += chunk
            address += chunk
        
        return bytes(result)

    def write(self, address: int, data_bytes: bytes | Sequence[int]) -> None:
        if not data_bytes:
            return
            
        address = address & _ADDR_MASK
        length = len(data_bytes)
        
        # Ultra-fast path: single page, hot cache hit
        pg = address >> _PAGE_SHIFT
        page_off = address & _PAGE_MASK
        
        if (pg == self._hot_page_num and self._hot_page_writable and 
            self._hot_page_data is not None and page_off + length <= PAGE_SIZE):
            self._hot_page_data[page_off:page_off + length] = data_bytes
            return
        
        # Single page path (most common)
        if (address >> _PAGE_SHIFT) == ((address + length - 1) >> _PAGE_SHIFT):
            if pg >= MAX_PAGES or not self._w_pages[pg]:
                raise PvmError(PAGE_FAULT(address))
            
            # Get or create page
            page_data = self._pages.get(pg)
            if page_data is None:
                page_data = bytearray(PAGE_SIZE)
                self._pages[pg] = page_data
            
            # Update hot cache
            self._hot_page_num = pg
            self._hot_page_data = page_data
            self._hot_page_writable = True
            
            page_data[page_off:page_off + length] = data_bytes
            return
        
        # Multi-page fallback (rare)
        self._write_multipage(address, data_bytes)
    
    def _write_multipage(self, address: int, data_bytes):
        """Separate multi-page write to keep main path fast."""
        if isinstance(data_bytes, bytes):
            data_mv = memoryview(data_bytes)
        else:
            data_mv = memoryview(bytes(data_bytes))
        
        length = len(data_bytes)
        end = address + length
        cursor = 0
        
        while address < end:
            pg = address >> _PAGE_SHIFT
            if pg >= MAX_PAGES or not self._w_pages[pg]:
                raise PvmError(PAGE_FAULT(address))
            
            page_off = address & _PAGE_MASK
            chunk = min(PAGE_SIZE - page_off, end - address)
            
            page_data = self._pages.get(pg)
            if page_data is None:
                page_data = bytearray(PAGE_SIZE)
                self._pages[pg] = page_data
            
            page_data[page_off:page_off + chunk] = data_mv[cursor:cursor + chunk]
            
            cursor += chunk
            address += chunk

    def get_pages(self, address: int, length: int) -> list[int]:
        """Get list of page numbers spanning a memory range."""
        return get_pages(address, length)

    def is_accessible(self, address: int, length: int, access: Accessibility = Accessibility.READ) -> bool:
        """Optimized accessibility check with bitarray."""
        if length <= 0:
            return True
            
        pages = self.get_pages(address, length)
        if access == Accessibility.WRITE:
            return all(self._w_pages[pg] for pg in pages if pg < MAX_PAGES)
        elif access == Accessibility.READ:
            return all((self._r_pages[pg] or self._w_pages[pg]) for pg in pages if pg < MAX_PAGES)
        return True

    # repr / equality keep old behaviour for debugging or tests  
    def __repr__(self) -> str:
        # Simplified repr to avoid expensive calculations during logging
        return f"Memory(pages={len(self._pages)}, heap={self.heap_break})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
            
        # Compare permission bits (sample or full check for large)
        if len(self._r_pages) != len(other._r_pages) or len(self._w_pages) != len(other._w_pages):
            return False
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
            
        print(read_pages)

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
        print(write_pages)

        arg_start = 2**32 - PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE
        read_pages.extend(get_pages(arg_start, total_page_size(len(args))))
        # print(f"ARG \t\t | START: {int(arg_start).to_bytes(4).hex()}")
        for i, byt in enumerate(args):
            memory[arg_start + i] = int(byt)

        return cls(memory, read_pages, write_pages, heap=heap)

    def zero_memory_range(self, start_page: int, num_pages: int) -> None:
        """Optimized memory zeroing."""
        if num_pages <= 0:
            return
            
        for page_idx in range(start_page, start_page + num_pages):
            # Create or get existing page
            page_data = self._page_for(page_idx * PAGE_SIZE, create=True)
            # Fast zero fill
            if isinstance(page_data, bytearray):
                page_data[:] = b'\x00' * PAGE_SIZE
            else:
                # Replace with a new zeroed bytearray
                zeroed_page = bytearray(PAGE_SIZE)
                self._pages[page_idx] = zeroed_page

    def alter_accessibility(self, start: int, len_: int, access: Accessibility) -> None:
        """Optimized accessibility alteration."""
        pages = get_pages(start, len_)
        
        for pg in pages:
            if pg >= MAX_PAGES:
                continue
            
            current_write = self._w_pages[pg]
            current_read = self._r_pages[pg]
            
            target_write = access == Accessibility.WRITE
            target_read = access == Accessibility.READ
            
            # Skip if already correct
            if current_write == target_write and current_read == target_read:
                continue
            
            if target_write:
                self._w_pages[pg] = 1
                self._r_pages[pg] = 0
            elif target_read:
                self._r_pages[pg] = 1
                self._w_pages[pg] = 0
            else:
                self._r_pages[pg] = 0
                self._w_pages[pg] = 0
        
        # Invalidate hot page cache for affected pages
        for pg in pages:
            if pg < MAX_PAGES and pg == self._hot_page_num:
                self._hot_page_num = -1
                self._hot_page_data = None
                self._hot_page_writable = False
                break

_ZERO_PAGE = bytes(PAGE_SIZE)

# Export INT_Memory as Memory for backward compatibility
Memory = INT_Memory
