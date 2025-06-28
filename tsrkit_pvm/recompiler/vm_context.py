import ctypes
import mmap
from tsrkit_types import TypedArray, structure, U64
from tsrkit_asm import Reg 

num_reg = 13

r_map = [
    Reg.rdi, 
    Reg.rax, 
    Reg.rsi, 
    Reg.rbx, 
    Reg.rdi, 
    Reg.rbp, 
    Reg.r8, 
    Reg.r9, 
    Reg.r10, 
    Reg.r11, 
    Reg.r12, 
    Reg.r13, 
    Reg.r14
]

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
