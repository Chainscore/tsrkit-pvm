# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: nonecheck=False
# cython: cdivision=True
# cython: profile=False
# cython: linetrace=False
# cython: embedsignature=True
# cython: initializedcheck=False
# cython: overflowcheck=False
# cython: infer_types=True
# cython: optimize.unpack_method_calls=True

cimport cython
from libc.stdint cimport int32_t, uint32_t, uint8_t
from libc.stdlib cimport malloc, free
from .cy_status cimport PvmExit, PVM_PANIC, PVM_HALT
from ..common.constants import PVM_ADDR_ALIGNMENT
from .mapper cimport inst_map
from tsrkit_types.integers import Uint
from tsrkit_types import Bits


cdef class CyProgram:
    def __cinit__(self):
        # ensure safe defaults even on constructor failure
        self._skip_cache = NULL
        self._skip_cache_len = 0
        self.zeta = NULL
        self.zeta_len = 0

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
        
        # Allocate and initialize zeta as C array for ultra-fast access
        cdef int32_t total_len = self.instruction_set_len + 1000
        self.zeta_len = total_len
        self.zeta = <uint8_t*>malloc(total_len * sizeof(uint8_t))
        if self.zeta == NULL:
            raise MemoryError("failed to allocate zeta buffer")
        
        # Copy instruction set to C array with padding
        cdef int32_t i
        for i in range(self.instruction_set_len):
            self.zeta[i] = self.instruction_set[i]
        # Zero-fill padding bytes
        for i in range(self.instruction_set_len, total_len):
            self.zeta[i] = 0
            
        self._exec_blocks      = {}

        self._precompute_cache()

    @cython.cfunc
    @cython.inline
    cdef _precompute_cache(self):
        """Optimized cache precomputation with fast C loops."""
        # pre-compute skip cache with optimized loop
        cdef int32_t bitmask_len = len(self.offset_bitmask)
        self._skip_cache_len     = bitmask_len
        self._skip_cache         = <int32_t*>malloc(bitmask_len * sizeof(int32_t))
        if self._skip_cache == NULL:
            raise MemoryError("failed to allocate skip-cache")

        cdef int32_t i, j, skip_value
        cdef int32_t extended_len = len(self._extended_bitmask)
        
        # Optimized skip cache computation with minimal Python calls
        for i in range(bitmask_len):
            skip_value = bitmask_len
            for j in range(i + 1, min(bitmask_len + 1, extended_len)):
                if self._extended_bitmask[j]:
                    skip_value = j - i - 1
                    break
            # Use bit operation for min(24, skip_value)
            self._skip_cache[i] = skip_value if skip_value < 24 else 24

        # compute basic blocks with optimized loop and pre-allocation
        cdef uint8_t opcode
        cdef list bb = [0]
        cdef int32_t instruction_len = self.instruction_set_len
        
        # Fast basic block computation with minimal overhead
        for i in range(instruction_len):
            if self.offset_bitmask[i]:
                opcode = self.instruction_set[i]
                # Optimized termination check with early exit
                if (opcode < 256 and 
                    inst_map.is_terminating(opcode) and 
                    inst_map._dispatch_table[opcode] != <void*>0):
                    bb.append(i + 1 + self._skip_cache[i])  # Use cached skip value
                    
        self.basic_blocks      = bb
        self._basic_blocks_set = set(bb)

    # ---------------------------------------------------------------- dealloc
    def __dealloc__(self):
        if self._skip_cache != NULL:
            free(self._skip_cache)
        if self.zeta != NULL:
            free(self.zeta)

    # ------------------------------------------------------------ fast helpers
    @cython.cfunc
    @cython.inline
    cdef uint32_t skip(self, int32_t pc) nogil:
        """Ultra-fast skip lookup with bounds checking optimized away."""
        if pc < 0 or pc >= self._skip_cache_len:
            return 0
        return self._skip_cache[pc]

    @cython.cfunc
    @cython.inline
    cdef uint32_t branch(self, int32_t counter, int32_t branch, bint cond):
        """Optimized conditional branch with fast set lookup."""
        if not cond:
            return <uint32_t>0xFFFF_FFFF
        if branch not in self._basic_blocks_set:
            raise PvmExit(PVM_PANIC)
        return branch

    @cython.cfunc
    @cython.inline  
    cdef uint32_t djump(self, uint32_t counter, uint32_t a):
        """Optimized dynamic jump with safer type handling."""
        # halt sentinel - original comparison
        if a == 0xFFFF_FFFF - 0xFFFF:
            raise PvmExit(PVM_HALT)

        # address sanity - keep original modulo check for safety
        if a == 0 or a % PVM_ADDR_ALIGNMENT:
            raise PvmExit(PVM_PANIC)

        cdef int32_t idx = <int32_t>(a // PVM_ADDR_ALIGNMENT) - 1
        if idx < 0 or idx >= self.jump_table_len:
            raise PvmExit(PVM_PANIC)

        cdef int32_t target = self.jump_table[idx]
        if target not in self._basic_blocks_set:
            raise PvmExit(PVM_PANIC)

        return target

    # Optimized encode/decode functions with C-level performance
    @cython.cfunc
    @cython.inline
    cdef int32_t encode_size(self):
        """
        Optimized size calculation with cached values.
        """
        cdef int32_t total = 0
        total += Uint(self.jump_table_len).encode_size()      # jump-table len (cached)
        total += 1                                            # z (1 byte)
        total += Uint(self.instruction_set_len).encode_size() # code len (cached)
        total += self.jump_table_len * self.z                 # jump entries (cached)
        total += self.instruction_set_len                     # code bytes (cached)
        total += Bits[self.instruction_set_len](self.offset_bitmask).encode_size()
        return total

    @cython.cfunc
    @cython.inline
    cdef int32_t encode_into(self, bytearray buffer, int32_t offset):
        """
        Optimized encoding with minimal Python object creation.
        """
        cdef int32_t curr = offset
        cdef int32_t i
        
        curr += Uint[self.jump_table_len](self.jump_table_len).encode_into(buffer, curr)
        curr += Uint[8](self.z).encode_into(buffer, curr)
        curr += Uint(self.instruction_set_len).encode_into(buffer, curr)

        # Optimized jump table encoding with C loop
        JumpInt = Uint[self.z * 8]
        for i in range(self.jump_table_len):
            curr += JumpInt(self.jump_table[i]).encode_into(buffer, curr)

        # copy instruction bytes with optimized memory operation
        buffer[curr:curr + self.instruction_set_len] = self.instruction_set
        curr += self.instruction_set_len

        # encode bitmask with cached length
        curr += Bits[self.instruction_set_len, "lsb"](self.offset_bitmask).encode_into(
            buffer, curr
        )
        return curr - offset

    @classmethod
    def decode_from(cls, buffer, offset: int = 0):
        """
        Optimized binary parsing with C-level performance.
        """
        cdef int32_t curr = offset
        cdef int32_t bytes_read = 0
        cdef int32_t j_len, c_len, sz
        cdef int32_t i, jump_val

        j_len, sz = Uint.decode_from(buffer, curr)
        bytes_read += sz
        curr += sz

        cdef int32_t z = buffer[curr]
        curr += 1
        bytes_read += 1

        c_len, sz = Uint.decode_from(buffer, curr)
        bytes_read += sz
        curr += sz

        # Optimized jump table decoding with pre-allocated list
        cdef list jump_table = []
        for i in range(j_len):
            jump_val = int.from_bytes(buffer[curr:curr + z], "little")
            jump_table.append(jump_val)
            curr += z
            bytes_read += z

        # instruction bytes with direct bytes conversion
        instruction_set = bytes(buffer[curr:curr + c_len])
        curr += c_len
        bytes_read += c_len

        # Optimized offset bitmask decoding with C-level bit operations
        cdef int32_t bit_bytes_needed = (c_len + 7) >> 3  # Faster than // 8
        bit_data = buffer[curr:curr + bit_bytes_needed]

        # Optimized bitmask decoding with C-level bit manipulation
        offset_bitmask = [False] * c_len
        cdef int32_t full_bytes = c_len >> 3  # Faster than // 8
        cdef int32_t byte_idx, bit_idx, base
        cdef uint8_t byte_val
        
        # Process full bytes with optimized bit extraction
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

        # Handle remaining bits with bit mask optimization
        cdef int32_t remaining = c_len & 7
        if remaining:
            byte_val = bit_data[full_bytes] if full_bytes < len(bit_data) else 0
            base = full_bytes << 3
            for bit_idx in range(remaining):
                offset_bitmask[base + bit_idx] = bool(byte_val & (1 << bit_idx))

        bytes_read += bit_bytes_needed
        curr += bit_bytes_needed

        return cls(z, jump_table, instruction_set, offset_bitmask), bytes_read
