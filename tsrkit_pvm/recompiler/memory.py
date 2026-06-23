import ctypes
import mmap
import os
from bitarray import bitarray
from tsrkit_pvm.common.types import Accessibility
from tsrkit_pvm.common.utils import get_pages, total_page_size, total_zone_size
from tsrkit_pvm.common.constants import (
    PVM_INIT_DATA_SIZE,
    PVM_INIT_ZONE_SIZE,
    PVM_MEMORY_PAGE_SIZE,
    PVM_MEMORY_TOTAL_SIZE,
)

PROT_NONE = 0

# Load libc for mprotect
if os.uname().sysname == "Darwin":
    libc = ctypes.CDLL("libc.dylib", use_errno=True)
else:
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
libc.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
libc.mprotect.restype = ctypes.c_int


class REC_Memory:
    buf: mmap.mmap
    buf_start = 0
    offset = -1
    heap_start = 0
    _r_pages: bitarray  # Track readable pages as bits
    _w_pages: bitarray  # Track writable pages as bits
    _closed = False  # Track if memory has been closed
    MAX_PAGES = 1 << 20  # 1M pages for 4GB address space

    def __init__(self, vm_size: int, heap_start=0):
        """
        Create an allocation for VM Context + Guest Memory
        Store pointer to the start of guest memory in self.offset
        """
        self.vm_size = (vm_size + mmap.PAGESIZE - 1) & ~(mmap.PAGESIZE - 1)
        self.buf = mmap.mmap(
            -1,
            length=PVM_MEMORY_TOTAL_SIZE + self.vm_size,
            flags=mmap.MAP_ANONYMOUS | mmap.MAP_PRIVATE,
        )
        self.buf_start = ctypes.addressof(ctypes.c_char.from_buffer(self.buf))
        self.offset = self.buf_start + self.vm_size
        self.heap_start = heap_start
        self._r_pages = bitarray(self.MAX_PAGES)
        self._r_pages.setall(0)
        self._w_pages = bitarray(self.MAX_PAGES)
        self._w_pages.setall(0)
        self._closed = False
        self._protect_guest_memory(PROT_NONE)

    def close(self):
        """Close the memory mapping and clean up resources"""
        if not self._closed and hasattr(self, 'buf'):
            try:
                self.buf.close()
                self._closed = True
            except:
                pass  # Ignore errors during cleanup

    def __del__(self):
        """Ensure cleanup on garbage collection"""
        self.close()

    def _protect_guest_memory(self, prot: int):
        res = libc.mprotect(
            ctypes.c_void_p(self.offset), PVM_MEMORY_TOTAL_SIZE, prot
        )
        if res != 0:
            error = ctypes.get_errno()
            print(f"Warning: mprotect failed for guest memory: {error}")

    def _page_prot(self, page: int) -> int:
        if page >= self.MAX_PAGES:
            return 0
        if self._w_pages[page]:
            return mmap.PROT_READ | mmap.PROT_WRITE
        if self._r_pages[page]:
            return mmap.PROT_READ
        return PROT_NONE

    def _mprotect_page(self, page: int, prot: int):
        if page >= self.MAX_PAGES:
            return
        start_addr = self.offset + page * PVM_MEMORY_PAGE_SIZE
        res = libc.mprotect(
            ctypes.c_void_p(start_addr), PVM_MEMORY_PAGE_SIZE, prot
        )
        if res != 0:
            error = ctypes.get_errno()
            print(f"Warning: mprotect failed for page {page}: {error}")

    @classmethod
    def from_initial(cls, initial_page_map: list, initial_data: list, vm_size: int):
        """Simplified initializer to support data from PVM test vectors. To be removed later"""

        mem = cls(vm_size)

        for pm in initial_page_map:
            access = Accessibility.WRITE if pm["is-writable"] else Accessibility.READ
            mem.alter_accessibility(pm["address"], pm["length"], access)

        for data in initial_data:
            mem.write_unchecked(data["address"], bytes(data["contents"]))

        return mem

    def zero_memory_range(self, start_page: int, num_pages: int):
        if num_pages <= 0:
            return
 
        size = num_pages * PVM_MEMORY_PAGE_SIZE
        self.write_unchecked(start_page * PVM_MEMORY_PAGE_SIZE, bytes(size))

    def alter_accessibility(self, start: int, len_: int, access: Accessibility):
 
        if access == Accessibility.WRITE:
            target_prot = mmap.PROT_READ | mmap.PROT_WRITE
        elif access == Accessibility.READ:
            target_prot = mmap.PROT_READ
        else:
            target_prot = 0  # PROT_NONE

        PAGE_SIZE = PVM_MEMORY_PAGE_SIZE

        pages = get_pages(start, len_)

        for pg in pages:
            if pg >= self.MAX_PAGES:
                continue  # Skip out-of-bounds pages

            # Determine current protection
            current_prot = 0
            if self._w_pages[pg]:
                current_prot = mmap.PROT_READ | mmap.PROT_WRITE
            elif self._r_pages[pg]:
                current_prot = mmap.PROT_READ

            if current_prot == target_prot:
                # Update bits to reflect the access
                if access == Accessibility.WRITE:
                    self._w_pages[pg] = 1
                    self._r_pages[pg] = 0
                elif access == Accessibility.READ:
                    self._r_pages[pg] = 1
                    self._w_pages[pg] = 0
                else:
                    self._r_pages[pg] = 0
                    self._w_pages[pg] = 0
                continue

            # Update bits
            if access == Accessibility.WRITE:
                self._w_pages[pg] = 1
                self._r_pages[pg] = 0
            elif access == Accessibility.READ:
                self._r_pages[pg] = 1
                self._w_pages[pg] = 0
            else:
                self._r_pages[pg] = 0
                self._w_pages[pg] = 0

            self._mprotect_page(pg, target_prot)

    @classmethod
    def from_pc(
        cls, read: bytes, write: bytes, args: bytes, z: int, s: int, vm_size: int
    ):
        """Creates memory as per GP"""
        mem = cls(vm_size)

        PAGE_SIZE = PVM_MEMORY_PAGE_SIZE

        # Calculate memory layout
        read_start = PVM_INIT_ZONE_SIZE
        read_length = total_page_size(len(read))
        read_pages = get_pages(read_start, read_length)

        write_start = 2 * PVM_INIT_ZONE_SIZE + total_zone_size(len(read))
        write_length = total_page_size(len(write)) + (int(z) * PVM_MEMORY_PAGE_SIZE)
        write_pages = get_pages(write_start, write_length)

        # Calculate heap
        mem.heap_start = int((write_pages[-1] + 1) * PVM_MEMORY_PAGE_SIZE)

        # Add stack pages to write pages
        stack_start = (
            2**32 - 2 * PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE - total_page_size(s)
        )
        stack_pages = get_pages(stack_start, total_page_size(s))
        write_pages.extend(stack_pages)

        # Calculate args location
        arg_start = 2**32 - PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE
        arg_pages = get_pages(arg_start, total_page_size(len(args)))
        read_pages.extend(arg_pages)

        # Write data FIRST before setting memory protections
        # Write read data
        guest_offset = vm_size + read_start
        mem.buf[guest_offset : guest_offset + len(read)] = read

        # Write write data
        guest_offset = vm_size + write_start
        mem.buf[guest_offset : guest_offset + len(write)] = write

        # Write args data
        guest_offset = vm_size + arg_start
        mem.buf[guest_offset : guest_offset + len(args)] = args

        # Set up memory protections for read pages (and make them executable)
        # Only set protection on pages that actually contain data or are explicitly needed
        for pg in read_pages:
            if pg < mem.MAX_PAGES:
                start_addr = mem.offset + pg * PAGE_SIZE
                # Page should already be aligned, but ensure it is
                aligned_addr = (start_addr // PAGE_SIZE) * PAGE_SIZE

                res = libc.mprotect(
                    ctypes.c_void_p(aligned_addr), PAGE_SIZE, mmap.PROT_READ
                )
                if res != 0:
                    error = ctypes.get_errno()
                    print(f"Warning: mprotect failed for read page {pg}: {error}")
                mem._r_pages[pg] = 1

        # Set up memory protections for write pages
        for pg in write_pages:
            if pg < mem.MAX_PAGES:
                start_addr = mem.offset + pg * PAGE_SIZE
                aligned_addr = (start_addr // PAGE_SIZE) * PAGE_SIZE

                res = libc.mprotect(
                    ctypes.c_void_p(aligned_addr),
                    PAGE_SIZE,
                    mmap.PROT_READ | mmap.PROT_WRITE,
                )
                if res != 0:
                    error = ctypes.get_errno()
                    print(f"Warning: mprotect failed for write page {pg}: {error}")
                mem._w_pages[pg] = 1

        return mem

    def is_accessible(self, address: int, length: int, access: Accessibility = Accessibility.READ) -> bool:
        """Check if memory range is accessible"""
        if length <= 0:
            return True
        pages = get_pages(address, length)
        if access == Accessibility.WRITE:
            return all(self._w_pages[pg] for pg in pages if pg < self.MAX_PAGES)
        elif access == Accessibility.READ:
            return all((self._r_pages[pg] or self._w_pages[pg]) for pg in pages if pg < self.MAX_PAGES)
        return True

    def read(self, address: int, length: int) -> bytes:
        """Read data from guest memory"""
        if length <= 0:
            return b""

        # For the recompiler, we can read directly from the buffer
        # The guest memory starts at vm_size offset in the buffer
        vm_size = self.offset - self.buf_start
        buffer_offset = vm_size + address

        try:
            return bytes(self.buf[buffer_offset : buffer_offset + length])
        except (IndexError, ValueError):
            # Return zeros if out of bounds (similar to interpreter behavior)
            return bytes(length)

    def write(self, address: int, data: bytes) -> None:
        """Write data to guest memory"""
        if not data:
            return

        length = len(data)

        # For the recompiler, we can write directly to the buffer
        # The guest memory starts at vm_size offset in the buffer
        vm_size = self.offset - self.buf_start
        buffer_offset = vm_size + address

        try:
            self.buf[buffer_offset : buffer_offset + length] = data
        except (IndexError, ValueError) as e:
            # Raise an exception if write is out of bounds
            raise IndexError(
                f"Memory write out of bounds: address={address}, length={length}"
            ) from e

    def write_unchecked(self, address: int, data: bytes) -> None:
        """Write test-vector data without changing final PVM page permissions."""
        if not data:
            return

        pages = get_pages(address, len(data))
        previous = [(pg, self._page_prot(pg)) for pg in pages if pg < self.MAX_PAGES]
        for pg, _ in previous:
            self._mprotect_page(pg, mmap.PROT_READ | mmap.PROT_WRITE)

        self.write(address, data)

        for pg, prot in previous:
            self._mprotect_page(pg, prot)
