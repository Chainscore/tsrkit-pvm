import ctypes
import mmap
import os
from tsrkit_pvm.common.types import Accessibility
from tsrkit_pvm.common.utils import get_pages, total_page_size, total_zone_size
from tsrkit_pvm.common.constants import (
    PVM_INIT_DATA_SIZE,
    PVM_INIT_ZONE_SIZE,
    PVM_MEMORY_PAGE_SIZE,
    PVM_MEMORY_TOTAL_SIZE,
)

# Load libc for mprotect
if os.uname().sysname == "Darwin":
    libc = ctypes.CDLL("libc.dylib")
else:
    libc = ctypes.CDLL("libc.so.6")


class REC_Memory:
    buf: mmap.mmap
    buf_start = 0
    offset = -1
    heap_start = 0
    _r_pages: set[int]  # Track readable pages
    _w_pages: set[int]  # Track writable pages

    def __init__(self, vm_size: int, heap_start=0):
        """
        Create an allocation for VM Context + Guest Memory
        Store pointer to the start of guest memory in self.offset
        """
        self.buf = mmap.mmap(
            -1,
            length=PVM_MEMORY_TOTAL_SIZE + vm_size,
            flags=mmap.MAP_ANONYMOUS | mmap.MAP_PRIVATE,
        )
        self.buf_start = ctypes.addressof(ctypes.c_char.from_buffer(self.buf))
        self.offset = self.buf_start + vm_size
        self.heap_start = heap_start
        self._r_pages = set()
        self._w_pages = set()

    @classmethod
    def from_initial(cls, initial_page_map: list, initial_data: list, vm_size: int):
        """Simplified initializer to support data from PVM test vectors. To be removed later"""

        mem = cls(vm_size)

        # Initialize memory data first
        for data in initial_data:
            # Use offset from VMContext to write to the correct location in guest memory
            guest_offset = vm_size + data["address"]
            mem.buf[guest_offset : guest_offset + len(data["contents"])] = bytes(
                data["contents"]
            )

        # Now, set up memory protections for mapped pages
        for pm in initial_page_map:
            prot = mmap.PROT_READ | mmap.PROT_WRITE
            # Calculate the actual memory address within our buffer
            start_addr = mem.buf_start + vm_size + pm["address"]

            # Ensure the address is page-aligned
            page_size = 4096  # Standard page size
            aligned_addr = (start_addr // page_size) * page_size

            res = libc.mprotect(ctypes.c_void_p(aligned_addr), pm["length"], prot)
            # mprotect returns 0 on success, -1 on failure
            if res != 0:
                error = ctypes.get_errno()
                print(
                    f"Warning: mprotect failed for address {hex(start_addr)}: {error}"
                )
                # Continue without failing - the memory might still be usable

        return mem

    def zero_memory_range(self, start_page: int, num_pages: int):
        if num_pages <= 0:
            return
 
        start_addr = self.offset + start_page * PVM_MEMORY_PAGE_SIZE
        size = num_pages * PVM_MEMORY_PAGE_SIZE
        self.buf[start_addr: start_addr + size] = bytes([0] * size)

    def alter_accessibility(self, start: int, len_: int, access: Accessibility):
 
        if access == Accessibility.WRITE:
            prot = mmap.PROT_WRITE
        elif access == Accessibility.READ:
            prot = mmap.PROT_READ
        else:
            prot = mmap.MAP_PRIVATE

        PAGE_SIZE = PVM_MEMORY_PAGE_SIZE

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

            start_addr = self.offset + pg * PAGE_SIZE
            aligned_addr = (start_addr // PAGE_SIZE) * PAGE_SIZE

            res = libc.mprotect(ctypes.c_void_p(aligned_addr), PAGE_SIZE, prot)
            if res != 0:
                error = ctypes.get_errno()
                print(f"Warning: mprotect failed for write page {pg}: {error}")


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
            start_addr = mem.offset + pg * PAGE_SIZE
            # Page should already be aligned, but ensure it is
            aligned_addr = (start_addr // PAGE_SIZE) * PAGE_SIZE

            res = libc.mprotect(
                ctypes.c_void_p(aligned_addr), PAGE_SIZE, mmap.PROT_READ
            )
            if res != 0:
                error = ctypes.get_errno()
                print(f"Warning: mprotect failed for read page {pg}: {error}")

        # Set up memory protections for write pages
        for pg in write_pages:
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

        # Track accessible pages for compatibility
        mem._r_pages.update(read_pages)
        mem._w_pages.update(write_pages)

        print("r", mem._r_pages, "w", mem._w_pages)
        return mem

    def is_accessible(self, address: int, length: int, access: Accessibility = Accessibility.READ) -> bool:
        """Check if memory range is accessible"""
        if length <= 0:
            return True
        pages = get_pages(address, length)
        if access == Accessibility.WRITE:
            return all(pg in self._w_pages for pg in pages)
        elif access == Accessibility.READ:
            return all(pg in self._r_pages or pg in self._w_pages for pg in pages)
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


# Alias for compatibility
GuestMemory = REC_Memory
