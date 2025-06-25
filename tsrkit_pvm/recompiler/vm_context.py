import ctypes
import mmap
from tsrkit_types import TypedArray, structure, U64

num_reg = 13

r_map = {
    0: 7, # RAX
    1: 0, # RCX
    2: 6, # RDX
    3: 3, # RBX
    4: 2, # RSP
    5: 5, # RBP
    6: 8,   # RSI
    7: 9,   # RDI
    8: 10,  # R8
    9: 11,  # R9
    10: 12, # R10
    11: 13, # R11
    12: 14  # R12
}


@structure
class VMContext:
    """VM context structure with 4 guest registers, and gas"""
    regs: TypedArray[U64, num_reg]
    gas: U64

    def store(self):
        encoded = self.encode()
        size = len(encoded)

        # Allocate RW access
        page_size = mmap.PAGESIZE
        alloc_size = (size + page_size - 1) & ~(page_size - 1)
        buf = mmap.mmap(-1, alloc_size, prot=mmap.PROT_WRITE | mmap.PROT_READ)
        buf.write(encoded)

        # Parse its address
        addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))

        print(f"VM Context of size {size}; stored at", addr)
        
        return buf, addr
