import ctypes
import mmap
import os

from tsrkit_pvm.interpreter.constants import PVM_MEMORY_PAGE_SIZE, PVM_MEMORY_TOTAL_SIZE

# Load libc for mprotect
if os.uname().sysname == "Darwin":
    libc = ctypes.CDLL("libc.dylib")
else:
    libc = ctypes.CDLL("libc.so.6")


class GuestMemory:
    buf: mmap.mmap
    offset = -1

    def __init__(self, vm_size: int):
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

    @classmethod
    def from_initial(cls, initial_page_map: list, initial_data: list, vm_size: int):
        """Simplified initializer to support data from PVM test vectors. To be removed later"""

        mem = cls(vm_size)

        # Set up memory protections for mapped pages
        for pm in initial_page_map:
            prot = (mmap.PROT_READ | mmap.PROT_WRITE)
            # Calculate the actual memory address within our buffer
            start_addr = mem.buf_start + vm_size + pm["address"]


            # Ensure the address is page-aligned
            page_size = 4096  # Standard page size
            aligned_addr = (start_addr // page_size) * page_size

            res = libc.mprotect(
                ctypes.c_void_p(aligned_addr), 
                pm["length"], 
                prot
            )
            # mprotect returns 0 on success, -1 on failure
            if res != 0:
                error = ctypes.get_errno()
                print(f"Warning: mprotect failed for address {hex(start_addr)}: {error}")
                # Continue without failing - the memory might still be usable

        # Initialize memory data
        for data in initial_data:
            # Use offset from VMContext to write to the correct location in guest memory
            guest_offset = vm_size + data["address"]
            mem.buf[guest_offset : guest_offset + len(data["contents"])] = bytes(
                data["contents"]
            )

        return mem

    def alter_accessibility(self, start: int, len_: int, is_write = True):
        prot = (mmap.PROT_READ | mmap.PROT_WRITE)
        # Calculate the actual memory address within our buffer
        start_addr = self.offset + start

        # Ensure the address is page-aligned
        page_size = 4096  # Standard page size
        aligned_addr = (start_addr // page_size) * page_size

        res = libc.mprotect(
            ctypes.c_void_p(aligned_addr), 
            len_, 
            prot
        )
        # mprotect returns 0 on success, -1 on failure
        if res != 0:
            error = ctypes.get_errno()
            print(f"Warning: mprotect failed for address {hex(start_addr)}: {error}")
            # Continue without failing - the memory might still be usable

    @classmethod
    def from_pc(cls, read: bytes, write: bytes, args: bytes, z: int, s: int) -> int:
        """Creates memory as per GP"""
        ...
