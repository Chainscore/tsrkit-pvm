from tsrkit_asm.tsrkit_asm import RegIndex
import ctypes
import mmap
import struct
from tsrkit_types import U32, TypedArray, TypedVector, Uint, structure, U64
from tsrkit_asm import Reg

num_reg = 13
guest_mem_size = 2 * 1024 * 1024 * 1024

TEMP_REG = Reg.rcx

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

from .memory import REC_Memory

# Optimized binary layout - no tsrkit-types overhead for critical path
# Layout: [jump_table_entries...] [jump_table_len] [regs...] [gas] [ret_addr] [ret_stack] [heap_start]
heap_start_offset = -4
ret_stack_offset = heap_start_offset - 8
ret_add_offset = ret_stack_offset - 8
gas_offset = ret_add_offset - 8
regs_offset = gas_offset - (8 * num_reg)
jump_len_offset = regs_offset - 8

VMContext_REGS_FMT = f"<{num_reg}Q"  # 13 uint64 registers in little-endian
VMContext_FIXED_FMT = "<QQQQL"        # gas, ret_addr, ret_stack, jump_len, heap_start
VMContext_FIXED_SIZE = struct.calcsize(VMContext_FIXED_FMT)


class VMContext:
    """
    VM context with direct binary layout. Contains information about the current
    execution state, including registers, gas, return address, return stack pointer,
    and heap start. Designed for fast encoding/decoding with minimal overhead.
    
    """
    
    def __init__(
        self,
        jump_table: list[int],
        regs: list[int],
        gas: int = 0,
        ret_addr: int = 0,
        ret_stack: int = 0,
        heap_start: int = 0,
    ) -> None:
        assert len(regs) == num_reg, f"Expected {num_reg} registers, found {len(regs)}"
        
        # Store as native Python lists/ints for fast access
        self.jump_table = jump_table
        self.regs = regs
        self.gas = gas
        self.ret_addr = ret_addr
        self.ret_stack = ret_stack
        self.heap_start = heap_start

    @classmethod
    def calculate_size(cls, jump_len: int) -> int:
        # New layout: [jump_table] [jump_len] [regs] [gas] [ret_addr] [ret_stack] [heap_start]
        return (jump_len * 8 +  # jump table entries
                8 +             # jump_len (uint64)
                num_reg * 8 +   # registers
                8 + 8 + 8 +     # gas, ret_addr, ret_stack (uint64 each)
                4)              # heap_start (uint32)

    def encode_size(self) -> int:
        return self.calculate_size(len(self.jump_table))

    @classmethod 
    def from_pointer(cls, pointer: int, jump_len: int) -> "VMContext":
        """
        Decoding directly from memory using ctypes operations.
        Bypasses tsrkit-types completely for maximum performance.
        """
        # Read jump table from the beginning
        jump_array = (ctypes.c_uint64 * jump_len).from_address(pointer)
        jump_table = list(jump_array)
        
        # Read remaining fields sequentially
        offset = jump_len * 8
        
        # Read jump table length (for validation)
        stored_jump_len = ctypes.c_uint64.from_address(pointer + offset).value
        assert stored_jump_len == jump_len, f"Jump table length mismatch: {stored_jump_len} != {jump_len}"
        offset += 8
        
        # Read registers
        regs_array = (ctypes.c_uint64 * num_reg).from_address(pointer + offset)
        regs = list(regs_array)
        offset += num_reg * 8
        
        # Read gas
        gas = ctypes.c_uint64.from_address(pointer + offset).value
        offset += 8
        
        # Read ret_addr
        ret_addr = ctypes.c_uint64.from_address(pointer + offset).value
        offset += 8
        
        # Read ret_stack
        ret_stack = ctypes.c_uint64.from_address(pointer + offset).value
        offset += 8
        
        # Read heap_start
        heap_start = ctypes.c_uint32.from_address(pointer + offset).value
        
        return cls(jump_table, regs, gas, ret_addr, ret_stack, heap_start)

    def encode(self) -> bytes:
        """
        Fast encoding using struct.pack.
        Layout: [jump_table] [jump_len] [regs] [gas] [ret_addr] [ret_stack] [heap_start]
        """
        jump_len = len(self.jump_table)
        
        # Pack in the order expected by from_pointer and store methods
        parts = []
        
        # Jump table
        parts.append(struct.pack(f"<{jump_len}Q", *self.jump_table))
        
        # Jump table length
        parts.append(struct.pack("<Q", jump_len))
        
        # Registers
        parts.append(struct.pack(VMContext_REGS_FMT, *self.regs))
        
        # Gas, ret_addr, ret_stack
        parts.append(struct.pack("<QQQ", self.gas, self.ret_addr, self.ret_stack))
        
        # Heap start
        parts.append(struct.pack("<L", self.heap_start))
        
        return b''.join(parts)

    def store(self, guest: REC_Memory, logger=None) -> tuple[int, int]:
        """
        Fast storage using direct memory operations.
        """
        size = self.encode_size()
        vm_pointer = guest.offset - size

        # Allocate RW access
        libc.mprotect(vm_pointer, size, prot=mmap.PROT_WRITE | mmap.PROT_READ)

        # Write data directly to memory using ctypes for maximum performance
        jump_len = len(self.jump_table)
        
        # Create ctypes arrays pointing to the memory locations
        memory_ptr = ctypes.cast(vm_pointer, ctypes.POINTER(ctypes.c_char))
        
        # Write jump table at the beginning
        jump_array = (ctypes.c_uint64 * jump_len)(*self.jump_table)
        ctypes.memmove(memory_ptr, jump_array, jump_len * 8)
        
        # Write jump table length
        offset = jump_len * 8
        jump_len_value = ctypes.c_uint64(jump_len)
        ctypes.memmove(ctypes.byref(memory_ptr.contents, offset), ctypes.byref(jump_len_value), 8)
        
        # Write registers
        offset += 8
        regs_array = (ctypes.c_uint64 * num_reg)(*self.regs)
        ctypes.memmove(ctypes.byref(memory_ptr.contents, offset), regs_array, num_reg * 8)
        
        # Write gas
        offset += num_reg * 8
        gas_value = ctypes.c_uint64(self.gas)
        ctypes.memmove(ctypes.byref(memory_ptr.contents, offset), ctypes.byref(gas_value), 8)
        
        # Write ret_addr
        offset += 8
        ret_addr_value = ctypes.c_uint64(self.ret_addr)
        ctypes.memmove(ctypes.byref(memory_ptr.contents, offset), ctypes.byref(ret_addr_value), 8)
        
        # Write ret_stack
        offset += 8
        ret_stack_value = ctypes.c_uint64(self.ret_stack)
        ctypes.memmove(ctypes.byref(memory_ptr.contents, offset), ctypes.byref(ret_stack_value), 8)
        
        # Write heap_start
        offset += 8
        heap_start_value = ctypes.c_uint32(self.heap_start)
        ctypes.memmove(ctypes.byref(memory_ptr.contents, offset), ctypes.byref(heap_start_value), 4)

        if logger:
            logger.debug(f"VM Context of size {size}; stored at {vm_pointer}")

        return vm_pointer, size