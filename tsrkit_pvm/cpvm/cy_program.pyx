# cython: language_level=3
# cython: boundscheck=False, wraparound=False, nonecheck=False, cdivision=True
# cython: profile=False, embedsignature=True

"""
Cython optimized INT_Program implementation.

This provides the same interface as interpreter/program.py but with C-level performance
for skip calculations, basic block management, and branching operations.
"""

cimport cython
from libc.stdint cimport int32_t, uint32_t, uint64_t, uint8_t
from libc.stdlib cimport malloc, free
from libc.math cimport floor
from typing import Any, Dict, Tuple, Union

from .cy_status cimport PvmError, CONTINUE, PVM_PANIC, HALT
from ..common.constants import PVM_ADDR_ALIGNMENT
from .mapper cimport inst_map
from tsrkit_types.integers import Uint   # ← use same helper as Python version
from tsrkit_types import Bits

cdef class CyProgram:
    """
    Cython-optimized INT_Program with fast skip cache and basic block operations.
    
    This class inherits from the base Program class but adds Cython optimizations
    for critical execution path operations.
    """
    
    # ----------------------------------------------------------------- cinit
    def __cinit__(self):
        # ensure safe defaults even on constructor failure
        self._skip_cache = NULL
        self._skip_cache_len = 0

    # ------------------------------------------------------------------ init
    def __init__(
        self,
        int32_t z,
        list    jump_table,
        bytes   instruction_set,
        list    offset_bitmask,
    ):
        # populate Python / C attributes ----------------------------------
        self.z               = z
        self.jump_table      = jump_table
        self.instruction_set = instruction_set
        self.offset_bitmask  = offset_bitmask
        self.basic_blocks    = []

        self.instruction_set_len = len(instruction_set)
        self.jump_table_len      = len(jump_table)

        self._extended_bitmask = self.offset_bitmask + [True] * 1000
        self.zeta              = self.instruction_set + bytes([0] * 1000)
        self._exec_blocks      = {}

        self._precompute_cache()

    cdef _precompute_cache(self):
        # pre-compute skip cache ------------------------------------------
        cdef int32_t bitmask_len = len(self.offset_bitmask)
        self._skip_cache_len     = bitmask_len
        self._skip_cache         = <int32_t*>malloc(bitmask_len * sizeof(int32_t))
        if self._skip_cache == NULL:
            raise MemoryError("failed to allocate skip-cache")

        cdef int32_t i, j, skip_value
        for i in range(bitmask_len):
            skip_value = bitmask_len
            for j in range(i + 1, bitmask_len + 1):
                if j < len(self._extended_bitmask) and self._extended_bitmask[j]:
                    skip_value = j - i - 1
                    break
            self._skip_cache[i] = min(24, skip_value)

        # compute basic blocks --------------------------------------------
        cdef uint8_t opcode
        cdef list bb = [0]
        for i in range(self.instruction_set_len):
            if self.offset_bitmask[i]:
                opcode = self.instruction_set[i]
                if (
                    opcode < 256
                    and inst_map.is_terminating(opcode)
                    and inst_map._dispatch_table[opcode] is not None
                ):
                    bb.append(i + 1 + self.skip(i))
        self.basic_blocks      = bb
        self._basic_blocks_set = set(bb)

    # ---------------------------------------------------------------- dealloc
    def __dealloc__(self):
        if self._skip_cache != NULL:
            free(self._skip_cache)

    # ------------------------------------------------------------ fast helpers
    cdef uint32_t skip(self, int32_t pc):
        return 0 if pc < 0 or pc >= self._skip_cache_len else self._skip_cache[pc]

    cdef tuple branch(self, int32_t counter, int32_t branch, bint cond):
        if not cond:
            return CONTINUE, counter
        if branch not in self._basic_blocks_set:
            raise PvmError(PVM_PANIC)
        return CONTINUE, branch

    cdef tuple djump(self, uint32_t counter, uint32_t a):
        # halt sentinel ----------------------------------------------------
        if a == 0xFFFF_FFFF - 0xFFFF:
            return HALT, counter

        # address sanity ---------------------------------------------------
        if a == 0 or a % PVM_ADDR_ALIGNMENT:
            raise PvmError(PVM_PANIC)

        cdef int32_t idx = <int32_t>(a // PVM_ADDR_ALIGNMENT) - 1
        if idx < 0 or idx >= self.jump_table_len:
            raise PvmError(PVM_PANIC)

        cdef int32_t target = self.jump_table[idx]
        if target not in self._basic_blocks_set:
            raise PvmError(PVM_PANIC)

        return CONTINUE, target

    # (encode_size / encode_into / decode_from unchanged)
    cdef int32_t encode_size(self):
        """
        Same formula as Program.encode_size.
        """
        cdef int32_t total = 0
        total += Uint(len(self.jump_table)).encode_size()     # jump-table len
        total += 1                                            # z (1 byte)
        total += Uint(len(self.instruction_set)).encode_size()# code len
        total += len(self.jump_table) * self.z                # jump entries
        total += self.instruction_set_len                     # code bytes
        total += Bits[self.instruction_set_len](self.offset_bitmask).encode_size()
        return total

    cdef int32_t encode_into(self, bytearray buffer, int32_t offset):
        """
        Byte-for-byte compatible with Program.encode_into
        """
        cdef int32_t curr = offset
        curr += Uint[len(self.jump_table)](len(self.jump_table)).encode_into(buffer, curr)
        curr += Uint[8](self.z).encode_into(buffer, curr)
        curr += Uint(len(self.instruction_set)).encode_into(buffer, curr)

        cdef int i
        JumpInt = Uint[self.z * 8]
        for i in range(self.jump_table_len):
            curr += JumpInt(self.jump_table[i]).encode_into(buffer, curr)

        # copy instruction bytes
        buffer[curr:curr + self.instruction_set_len] = self.instruction_set
        curr += self.instruction_set_len

        # bitmask
        curr += Bits[self.instruction_set_len, "lsb"](self.offset_bitmask).encode_into(
            buffer, curr
        )
        return curr - offset

    @classmethod
    def decode_from(cls, buffer, offset: int = 0):
        """
        Parse the binary produced by encode_into and return (CyProgram, bytes_read)
        """
        cdef int curr = offset
        cdef int bytes_read = 0

        j_len, sz = Uint.decode_from(buffer, curr)
        bytes_read += sz
        curr += sz

        z = buffer[curr]
        curr += 1
        bytes_read += 1

        c_len, sz = Uint.decode_from(buffer, curr)
        bytes_read += sz
        curr += sz

        # jump table -------------------------------------------------------
        cdef list jump_table = []
        cdef int i
        for i in range(j_len):
            jump_val = int.from_bytes(buffer[curr:curr + z], "little")
            jump_table.append(jump_val)
            curr += z
            bytes_read += z

        # instruction bytes ------------------------------------------------
        instruction_set = bytes(buffer[curr:curr + c_len])
        curr += c_len
        bytes_read += c_len

        # offset bitmask ---------------------------------------------------
        bit_bytes_needed = (c_len + 7) // 8
        bit_data = buffer[curr:curr + bit_bytes_needed]

        offset_bitmask = [False] * c_len
        full_bytes = c_len // 8
        for byte_idx in range(full_bytes):
            byte_val = bit_data[byte_idx]
            base = byte_idx << 3
            offset_bitmask[base]     = bool(byte_val & 1)
            offset_bitmask[base + 1] = bool(byte_val & 2)
            offset_bitmask[base + 2] = bool(byte_val & 4)
            offset_bitmask[base + 3] = bool(byte_val & 8)
            offset_bitmask[base + 4] = bool(byte_val & 16)
            offset_bitmask[base + 5] = bool(byte_val & 32)
            offset_bitmask[base + 6] = bool(byte_val & 64)
            offset_bitmask[base + 7] = bool(byte_val & 128)

        remaining = c_len & 7
        if remaining:
            byte_val = bit_data[full_bytes] if full_bytes < len(bit_data) else 0
            base = full_bytes << 3
            for bit_idx in range(remaining):
                offset_bitmask[base + bit_idx] = bool(byte_val & (1 << bit_idx))

        bytes_read += bit_bytes_needed
        curr += bit_bytes_needed

        return cls(z, jump_table, instruction_set, offset_bitmask), bytes_read
