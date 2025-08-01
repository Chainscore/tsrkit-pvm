from tsrkit_asm.tsrkit_asm import RegIndex
import ctypes
import mmap
from tsrkit_types import U32, TypedArray, TypedVector, Uint, structure, U64
from tsrkit_asm import Reg

num_reg = 13
guest_mem_size = 2 * 1024 * 1024 * 1024

r_map = [
    Reg.rdi,  # PVM r0
    Reg.rax,  # PVM r1
    Reg.rsi,  # PVM r2
    Reg.rbx,  # PVM r3
    Reg.rdx,  # PVM r4
    Reg.rbp,  # PVM r5
    Reg.r8,  # PVM r6
    Reg.r9,  # PVM r7
    Reg.r10,  # PVM r8
    Reg.r11,  # PVM r9
    Reg.r12,  # PVM r10
    Reg.r13,  # PVM r11
    Reg.r14,  # PVM r12
]

rindex_map = [
    RegIndex.rdi,
    RegIndex.rax,  # PVM r1
    RegIndex.rsi,  # PVM r2
    RegIndex.rbx,  # PVM r3
    RegIndex.rdx,  # PVM r4
    RegIndex.rbp,  # PVM r5
    RegIndex.r8,  # PVM r6
    RegIndex.r9,  # PVM r7
    RegIndex.r10,  # PVM r8
    RegIndex.r11,  # PVM r9
    RegIndex.r12,  # PVM r10
    RegIndex.r13,  # PVM r11
    RegIndex.r14,  # PVM r12
]

import os

# Load libc for mprotect
if os.uname().sysname == "Darwin":
    libc = ctypes.CDLL("libc.dylib")
else:
    libc = ctypes.CDLL("libc.so.6")

from .memory import GuestMemory

ret_stack_offset = - 8
ret_add_offset = ret_stack_offset - 8
gas_offset = ret_add_offset - 8
regs_offset = gas_offset - (8 * num_reg)
jump_len_offset = regs_offset - 8


@structure
class VMContext:
    """VM context structure with 4 guest registers, gas, and jump table"""
    # --- Jump Table --- #
    jump_table: TypedArray[U64]
    jump_table_len: U64
    # --- Registers --- #
    regs: TypedArray[U64, num_reg]
    # --- Gas --- #
    gas: U64
    # --- SF Handler Info --- #
    ret_addr: U64
    ret_stack: U64

    def __init__(
        self, 
        jump_table: list[int], 
        regs: list[int], 
        gas = 0, 
        ret_addr = 0, 
        ret_stack = 0
    ):
        self.jump_table = TypedArray[U64, len(jump_table)]([U64(j) for j in jump_table])
        self.jump_table_len = U64(len(jump_table))
        assert len(regs) == num_reg, f"Expected {num_reg} registers, found {len(regs)}"
        self.regs = TypedArray[U64, num_reg]([U64(r) for r in regs])
        self.gas = U64(gas)
        self.ret_addr = U64(ret_addr)
        self.ret_stack = U64(ret_stack)

    @classmethod
    def calculate_size(cls, jump_len: int):
        return abs(jump_len_offset) + jump_len * 8

    def encode_size(self):
        return abs(jump_len_offset) + self.jump_table.encode_size()

    @classmethod
    def from_pointer(cls, pointer: int, jump_len: int):
        buf_len = cls.calculate_size(jump_len)
        buffer = ctypes.string_at(pointer, buf_len)

        ret_stack = U64.decode(buffer[ret_stack_offset:])
        ret_addr = U64.decode(buffer[ret_add_offset:])
        gas = U64.decode(buffer[gas_offset:])
        regs = TypedArray[U64, num_reg].decode(buffer[regs_offset:])
        jump_table_len = U64.decode(buffer[jump_len_offset:])
        jump_table = TypedArray[U64, jump_table_len].decode(buffer)

        return cls(jump_table, regs, gas, ret_addr, ret_stack)

    def store(self, guest: GuestMemory, logger = None):
        encoded = self.encode()
        size = len(encoded)

        assert size == self.calculate_size(len(self.jump_table))

        vm_pointer = guest.offset - self.calculate_size(len(self.jump_table))

        # Allocate RW access
        libc.mprotect(vm_pointer, size, prot=mmap.PROT_WRITE | mmap.PROT_READ)

        # Write to its buffer
        ctypes.memmove(vm_pointer, encoded, size)

        if logger: logger.debug(f"VM Context of size {size}; stored at", vm_pointer)

        return vm_pointer, size
