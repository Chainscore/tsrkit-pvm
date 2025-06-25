import ctypes
import mmap
import os

from tsrkit_pvm.interpreter.constants import PVM_MEMORY_PAGE_SIZE, PVM_MEMORY_TOTAL_SIZE

# Load libc for mprotect
if os.uname().sysname == "Darwin":
    libc = ctypes.CDLL("libc.dylib")
else:
    libc = ctypes.CDLL("libc.so.6")


class Memory:
    buf = None
    offset = -1

    @classmethod
    def from_initial(cls, initial_page_map: list, initial_data: list):
        cls.buf = mmap.mmap(-1, length=PVM_MEMORY_TOTAL_SIZE, flags=mmap.MAP_ANONYMOUS | mmap.MAP_PRIVATE)
        cls.offset = ctypes.addressof(ctypes.c_char.from_buffer(cls.buf))
        
        for pm in initial_page_map:
            prot = mmap.PROT_READ if not pm["is-writable"] else mmap.PROT_READ | mmap.PROT_WRITE
            res = libc.mprotect(ctypes.c_void_p(cls.offset + pm["address"]), pm["length"], prot)
            if res != 0:
                error = ctypes.get_errno()
                raise OSError(error, "mprotect failed ot set permissions")
        
        for data in initial_data:
            cls.buf[data["address"]: len(data["contents"])] = bytes(data["contents"])
        
        return cls()

    @classmethod
    def from_pc(cls, read: bytes, write: bytes, args: bytes, z: int, s: int) -> int:
        ...
