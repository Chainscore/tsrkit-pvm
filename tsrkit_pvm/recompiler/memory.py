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

    def __init__(self):
        """
        Create an allocation for VM Context + Guest Memory
        Store pointer to the start of guest memory in self.offset
        """
        from tsrkit_pvm.recompiler.vm_context import VMContext
        
        self.buf = mmap.mmap(
            -1, 
            length=PVM_MEMORY_TOTAL_SIZE + VMContext.encode_size(), 
            flags=mmap.MAP_ANONYMOUS | mmap.MAP_PRIVATE
        )
        self.buf_start = ctypes.addressof(ctypes.c_char.from_buffer(self.buf)) 
        self.offset = self.buf_start + VMContext.encode_size()
        
    @classmethod
    def from_initial(cls, initial_page_map: list, initial_data: list):
        """Simplified initializer to support data from PVM test vectors. To be removed later"""
        mem = cls()

        for pm in initial_page_map:
            prot = mmap.PROT_READ if not pm["is-writable"] else mmap.PROT_READ | mmap.PROT_WRITE
            res = libc.mprotect(
                ctypes.c_void_p(mem.offset + pm["address"]), 
                pm["length"], 
                prot
            )
            if res != 0:
                error = ctypes.get_errno()
                raise OSError(error, "mprotect failed ot set permissions")
        
        for data in initial_data:
            mem.buf[data["address"]: len(data["contents"])] = bytes(data["contents"])
        
        return mem

    @classmethod
    def from_pc(cls, read: bytes, write: bytes, args: bytes, z: int, s: int) -> int:
        """Creates memory as per GP"""
        ...
