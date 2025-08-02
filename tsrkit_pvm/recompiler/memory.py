import ctypes
import mmap
import os
from tsrkit_pvm.common.utils import get_pages, total_page_size, total_zone_size
from tsrkit_pvm.common.constants import PVM_INIT_DATA_SIZE, PVM_INIT_ZONE_SIZE, PVM_MEMORY_PAGE_SIZE, PVM_MEMORY_TOTAL_SIZE

# Load libc for mprotect
if os.uname().sysname == "Darwin":
    libc = ctypes.CDLL("libc.dylib")
else:
    libc = ctypes.CDLL("libc.so.6")


class REC_Memory:
    buf: mmap.mmap
    offset = -1
    heap_start = 0

    def __init__(self, vm_size: int, heap_start = 0):
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

    @classmethod
    def from_initial(cls, initial_page_map: list, initial_data: list, vm_size: int):
        """Simplified initializer to support data from PVM test vectors. To be removed later"""

        mem = cls(vm_size)

        # Set up memory protections for mapped pages
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

        # Initialize memory data
        for data in initial_data:
            # Use offset from VMContext to write to the correct location in guest memory
            guest_offset = vm_size + data["address"]
            mem.buf[guest_offset : guest_offset + len(data["contents"])] = bytes(
                data["contents"]
            )

        return mem

    def alter_accessibility(self, start: int, len_: int, is_write=True):
        prot = mmap.PROT_READ | mmap.PROT_WRITE
        # Calculate the actual memory address within our buffer
        start_addr = self.offset + start

        # Ensure the address is page-aligned
        page_size = 4096  # Standard page size
        aligned_addr = (start_addr // page_size) * page_size

        res = libc.mprotect(ctypes.c_void_p(aligned_addr), len_, prot)
        # mprotect returns 0 on success, -1 on failure
        if res != 0:
            error = ctypes.get_errno()
            print(f"Warning: mprotect failed for address {hex(start_addr)}: {error}")
            # Continue without failing - the memory might still be usable

    @classmethod
    def from_pc(cls, read: bytes, write: bytes, args: bytes, z: int, s: int, vm_size: int = 1024):
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
        stack_start = 2**32 - 2 * PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE - total_page_size(s)
        stack_pages = get_pages(stack_start, total_page_size(s))
        write_pages.extend(stack_pages)
        
        # Calculate args location
        arg_start = 2**32 - PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE
        arg_pages = get_pages(arg_start, total_page_size(len(args)))
        read_pages.extend(arg_pages)
        
        # Set up memory protections for read pages
        for pg in read_pages:
            start_addr = mem.offset + pg * PAGE_SIZE
            aligned_addr = (start_addr // 4096) * 4096
            res = libc.mprotect(ctypes.c_void_p(aligned_addr), PAGE_SIZE, mmap.PROT_READ)
            if res != 0:
                error = ctypes.get_errno()
                print(f"Warning: mprotect failed for read page {pg}: {error}")
        
        # Set up memory protections for write pages
        for pg in write_pages:
            start_addr = mem.offset + pg * PAGE_SIZE
            aligned_addr = (start_addr // 4096) * 4096
            res = libc.mprotect(ctypes.c_void_p(aligned_addr), PAGE_SIZE, mmap.PROT_READ | mmap.PROT_WRITE)
            if res != 0:
                error = ctypes.get_errno()
                print(f"Warning: mprotect failed for write page {pg}: {error}")
        
        # Write read data
        guest_offset = vm_size + read_start
        mem.buf[guest_offset:guest_offset + len(read)] = read
        
        # Write write data
        guest_offset = vm_size + write_start
        mem.buf[guest_offset:guest_offset + len(write)] = write
        
        # Write args data
        guest_offset = vm_size + arg_start
        mem.buf[guest_offset:guest_offset + len(args)] = args
        
        return mem


# Alias for compatibility
GuestMemory = REC_Memory
