# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False  
# cython: cdivision=True
# cython: profile=True

"""
Cython optimized ii_reg instruction table.
Instructions with 2 register arguments (opcodes 100-111).
"""

from typing import Dict
from libc.stdint cimport uint32_t, int64_t, uint64_t, uint8_t, uint16_t, uint32_t

from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import b, b_inv, chi, compare, compare_bits_vectorized, z, z_inv, clamp_12
from tsrkit_pvm.core.instruction_table import InstructionTable
from tsrkit_pvm.core.opcode import OpCode, OpReturn
from ...cy_memory import WRITE
from ...cy_memory cimport CyMemory

cdef class CyInstructionsWArgs2Reg:
    """
    Cython optimized instruction table for instructions with 2 register arguments.
    """
    cdef uint32_t counter
    cdef object program
    cdef uint32_t skip_index
    
    def __init__(self, uint32_t counter, object program, uint32_t skip_index):
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    cpdef list get_props(self):
        """
        Extract register indices from program bytes.
        Returns [rd, ra] where rd is destination and ra is source register.
        """
        # Extract byte value using C-style operations for speed
        cdef uint8_t byte_val = self.program.zeta[self.counter + 1]
        cdef uint32_t rd = clamp_12(byte_val & 0x0F)  # Lower 4 bits
        cdef uint32_t ra = clamp_12(byte_val >> 4)    # Upper 4 bits
        return [rd, ra]
    
    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            100: OpCode(name="move_reg", fn=cls.move_reg, gas=1, is_terminating=False),
            101: OpCode(name="sbrk", fn=cls.sbrk, gas=1, is_terminating=False),
            102: OpCode(
                name="count_set_bits_64",
                fn=cls.count_set_bits_64,
                gas=1,
                is_terminating=False,
            ),
            103: OpCode(
                name="count_set_bits_32", 
                fn=cls.count_set_bits_32,
                gas=1,
                is_terminating=False,
            ),
            104: OpCode(
                name="leading_zero_bits_64",
                fn=cls.leading_zero_bits_64,
                gas=1,
                is_terminating=False,
            ),
            105: OpCode(
                name="leading_zero_bits_32",
                fn=cls.leading_zero_bits_32,
                gas=1,
                is_terminating=False,
            ),
            106: OpCode(
                name="trailing_zero_bits_64",
                fn=cls.trailing_zero_bits_64,
                gas=1,
                is_terminating=False,
            ),
            107: OpCode(
                name="trailing_zero_bits_32",
                fn=cls.trailing_zero_bits_32,
                gas=1,
                is_terminating=False,
            ),
            108: OpCode(
                name="sign_extend_8", fn=cls.sign_extend_8, gas=1, is_terminating=False
            ),
            109: OpCode(
                name="sign_extend_16",
                fn=cls.sign_extend_16,
                gas=1,
                is_terminating=False,
            ),
            110: OpCode(
                name="zero_extend_16",
                fn=cls.zero_extend_16,
                gas=1,
                is_terminating=False,
            ),
            111: OpCode(
                name="reverse_bytes", fn=cls.reverse_bytes, gas=1, is_terminating=False
            ),
        }

    cdef tuple  move_reg(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC100: Move value from register ra to register rd."""
        registers[rd] = registers[ra]
        return CONTINUE, -1

    cdef tuple  sbrk(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC101: Expand heap by ra bytes and store old break in rd."""
        cdef int64_t req = registers[ra]  # bytes requested
        memory.alter_accessibility(memory.heap_break, req, WRITE)
        
        # Store old heap break in destination register
        registers[rd] = memory.heap_break
        
        # Update heap break
        memory.heap_break = memory.heap_break + req
        
        return CONTINUE, -1

    # Bit counting instructions with C-level optimizations
    cdef tuple  count_set_bits_64(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC102: Count set bits in 64-bit value."""
        cdef uint64_t val = registers[ra] % (2**64)
        cdef uint32_t count = self._count_set_bits_c(val)
        registers[rd] = count
        return CONTINUE, -1

    cdef tuple  count_set_bits_32(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC103: Count set bits in 32-bit value."""
        cdef uint32_t val = registers[ra] % (2**32)
        cdef uint32_t count = self._count_set_bits_c(val)
        registers[rd] = count
        return CONTINUE, -1

    # Leading zero counting with C optimizations
    cdef tuple  leading_zero_bits_64(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC104: Count leading zero bits in 64-bit value."""
        cdef uint64_t val = registers[ra] % (2**64)
        cdef uint32_t count = self._leading_zeros_c(val, 64)
        registers[rd] = count
        return CONTINUE, -1

    cdef tuple  leading_zero_bits_32(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC105: Count leading zero bits in 32-bit value."""
        cdef uint32_t val = registers[ra] % (2**32)
        cdef uint32_t count = self._leading_zeros_c(val, 32)
        registers[rd] = count
        return CONTINUE, -1

    # Trailing zero counting with C optimizations  
    cdef tuple  trailing_zero_bits_64(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC106: Count trailing zero bits in 64-bit value."""
        cdef uint64_t val = registers[ra] % (2**64)
        cdef uint32_t count = self._trailing_zeros_c(val, 64)
        registers[rd] = count
        return CONTINUE, -1

    cdef tuple  trailing_zero_bits_32(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC107: Count trailing zero bits in 32-bit value."""
        cdef uint32_t val = registers[ra] % (2**32)
        cdef uint32_t count = self._trailing_zeros_c(val, 32)
        registers[rd] = count
        return CONTINUE, -1

    # Sign extension instructions
    cdef tuple  sign_extend_8(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC108: Sign extend 8-bit value to 64-bit."""
        registers[rd] = z_inv(
            z(registers[ra] % 2**8, 8 // 8), 8
        )
        return CONTINUE, -1

    cdef tuple  sign_extend_16(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC109: Sign extend 16-bit value to 64-bit."""
        registers[rd] = z_inv(
            z(registers[ra] % 2**16, 16 // 8), 8
        )
        return CONTINUE, -1

    cdef tuple  zero_extend_16(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC110: Zero extend 16-bit value to 64-bit."""
        cdef uint64_t val = registers[ra] % (2**16)
        registers[rd] = val
        return CONTINUE, -1

    cdef tuple  reverse_bytes(self, uint64_t *registers, CyMemory memory, uint32_t rd, uint32_t ra):
        """OPC111: Reverse byte order of 64-bit value."""
        # cdef uint64_t val = registers[ra]
        # cdef uint64_t reversed = (
        #     ((val & 0xFF) << 56) |
        #     ((val & 0xFF00) << 40) |
        #     ((val & 0xFF0000) << 24) |
        #     ((val & 0xFF000000) << 8) |
        #     ((val & 0xFF00000000) >> 8) |
        #     ((val & 0xFF0000000000) >> 24) |
        #     ((val & 0xFF000000000000) >> 40) |
        #     ((val & 0xFF00000000000000) >> 56)
        # )
        # registers[rd] = reversed
        registers[rd] = int.from_bytes(
            registers[ra].to_bytes(8, "little")[::-1], "little"
        )
        return CONTINUE, -1

    # ----------------------------#
    # ---- C helper functions ----#
    # ----------------------------#
    cdef uint32_t _count_set_bits_c(self, uint64_t val):
        """Fast bit counting using Brian Kernighan's algorithm."""
        cdef uint32_t count = 0
        while val:
            val &= val - 1  # Clear lowest set bit
            count += 1
        return count

    cdef uint32_t _leading_zeros_c(self, uint64_t val, uint32_t bitsize):
        """Count leading zeros with C-level bit operations."""
        if val == 0:
            return bitsize
        
        cdef uint32_t count = 0
        cdef uint64_t mask = 1ULL << (bitsize - 1)
        
        while (val & mask) == 0:
            count += 1
            mask >>= 1
            
        return count

    cdef uint32_t _trailing_zeros_c(self, uint64_t val, uint32_t bitsize):
        """Count trailing zeros with C-level bit operations."""
        if val == 0:
            return bitsize
            
        cdef uint32_t count = 0
        while (val & 1) == 0:
            count += 1
            val >>= 1
            
        return count

