import ctypes
import mmap
from tsrkit_types import TypedArray, structure, U64

@structure
class VMContext:
    """VM context structure with 4 guest registers, and gas"""
    regs: TypedArray[U64, 4]
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

r_map = {
    0: 7,
    1: 0,
    2: 6,
    3: 3
}
