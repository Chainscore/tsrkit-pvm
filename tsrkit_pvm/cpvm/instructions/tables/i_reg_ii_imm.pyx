# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 1 register + 2 immediate argument instructions.

This table handles instructions that take one register and two immediate arguments:
- store_imm_ind_u8/u16/u32/u64: Store immediate value at indirect address with offset
"""

from typing import Dict
from libc.stdint cimport uint32_t, uint64_t

from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import chi, clamp_12, clamp_4, clamp_4_max0
from tsrkit_pvm.core.opcode import OpCode

cdef class CyInstructionsWArgs1Reg2Imm:
    """
    Cython optimized instruction table for 1 register + 2 immediate argument instructions.
    
    This class provides high-performance implementations of instructions that
    take one register and two immediate arguments, including:
    - Memory store operations with immediate values at indirect addresses
    All optimized with Cython for maximum performance.
    """
    
    cdef public uint32_t counter
    cdef public object program  # INT_Program - keeping as Python object for now
    cdef public uint32_t skip_index
    
    def __init__(self, uint32_t counter, program, uint32_t skip_index):
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    cpdef list get_props(self):
        """
        Extract one register and two immediate arguments from the instruction stream.
        Returns [ra, lx, ly, vx, vy] where ra is register, lx/ly are lengths, vx/vy are immediates.
        """
        cdef uint32_t byte_val = self.program.zeta[self.counter + 1]
        cdef uint32_t ra = clamp_12(byte_val & 0x0F)           # Lower 4 bits
        cdef uint32_t lx = clamp_4((byte_val >> 4) & 0x07)     # Next 3 bits
        cdef uint32_t ly = clamp_4_max0(self.skip_index - lx - 1)
        
        # Extract first immediate value
        cdef uint32_t start = self.counter + 2
        cdef uint32_t end = start + lx
        cdef bytes vx_slice = self.program.zeta[start:end]
        cdef uint64_t vx = 0
        if lx > 0:
            vx = chi(int.from_bytes(vx_slice, "little"), lx)
        
        # Extract second immediate value
        start = self.counter + 2 + lx
        end = start + ly
        cdef bytes vy_slice = self.program.zeta[start:end]
        cdef uint64_t vy = 0
        if ly > 0:
            vy = chi(int.from_bytes(vy_slice, "little"), ly)
        
        return [ra, lx, ly, vx, vy]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            70: OpCode(name="store_imm_ind_u8", fn=cls.store_imm_ind_u8, gas=1, is_terminating=False),
            71: OpCode(name="store_imm_ind_u16", fn=cls.store_imm_ind_u16, gas=1, is_terminating=False),
            72: OpCode(name="store_imm_ind_u32", fn=cls.store_imm_ind_u32, gas=1, is_terminating=False),
            73: OpCode(name="store_imm_ind_u64", fn=cls.store_imm_ind_u64, gas=1, is_terminating=False),
        }

    # Store immediate indirect instructions
    cpdef tuple store_imm_ind_u8(self, list registers, object memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC70: Store immediate vy as u8 at address (ra + vx)."""
        value = int(vy % (2**8))
        memory.write(registers[ra] + vx, value.to_bytes(1, "little"))
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple store_imm_ind_u16(self, list registers, object memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC71: Store immediate vy as u16 at address (ra + vx)."""
        value = int(vy % (2**16))
        memory.write(registers[ra] + vx, value.to_bytes(2, "little"))
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple store_imm_ind_u32(self, list registers, object memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC72: Store immediate vy as u32 at address (ra + vx)."""
        value = int(vy % (2**32))
        memory.write(registers[ra] + vx, value.to_bytes(4, "little"))
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory

    cpdef tuple store_imm_ind_u64(self, list registers, object memory, uint32_t ra, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC73: Store immediate vy as u64 at address (ra + vx)."""
        value = int(vy % (2**64))
        memory.write(registers[ra] + vx, value.to_bytes(8, "little"))
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory
