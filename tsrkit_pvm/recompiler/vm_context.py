import ctypes
import mmap
from tsrkit_types import TypedArray, structure, U64
from tsrkit_asm import Reg 

num_reg = 13
guest_mem_size = 2 * 1024 * 1024 * 1024 

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

import os

# Load libc for mprotect
if os.uname().sysname == "Darwin":
    libc = ctypes.CDLL("libc.dylib")
else:
    libc = ctypes.CDLL("libc.so.6")


from .memory import GuestMemory

@structure
class VMContext:
    """VM context structure with 4 guest registers, and gas"""
    regs: TypedArray[U64, num_reg]
    gas: U64

    @classmethod
    def encode_size(cls):
        return 8 * num_reg + 8

    @classmethod
    def from_pointer(cls, pointer: int):
        buffer = ctypes.string_at(pointer, cls.encode_size())
        return cls.decode(buffer)

    def store(self, guest: GuestMemory):
        encoded = self.encode()
        size = len(encoded)

        
        vm_pointer = guest.offset - self.encode_size()
        print(f"guest offset {guest.offset} | vm pointer {vm_pointer}") 

        # Allocate RW access
        libc.mprotect(
            vm_pointer, 
            size,
            prot=mmap.PROT_WRITE | mmap.PROT_READ
        )
        
        # Write to its buffer
        ctypes.memmove(vm_pointer, encoded, size)

        print(f"VM Context of size {size}; stored at", vm_pointer)
        
        return vm_pointer
