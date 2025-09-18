# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 2 immediate argument instructions.

This table handles instructions that take two immediate arguments:
- store_imm_u8: Store immediate 8-bit value
- store_imm_u16: Store immediate 16-bit value  
- store_imm_u32: Store immediate 32-bit value
- store_imm_u64: Store immediate 64-bit value
"""

from typing import Dict
from libc.stdint cimport uint32_t, uint64_t, uint8_t, uint16_t, uint32_t
from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import chi, clamp_4, clamp_4_max0
from tsrkit_pvm.core.opcode import OpCode
from ...cy_memory cimport CyMemory


cdef class CyInstructionsWArgs2Imm:
    """
    Cython optimized instruction table for 2 immediate argument instructions.
    
    This class provides high-performance implementations of instructions that
    take two immediate arguments, optimized with Cython for speed.
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
        Extract two immediate arguments from the instruction stream.
        Returns [lx, ly, vx, vy] where lx/ly are lengths and vx/vy are the values.
        """
        cdef uint32_t lx = clamp_4(self.program.zeta[self.counter + 1])
        cdef uint32_t ly = clamp_4_max0(self.skip_index - int(lx) - 1)
        
        # Extract first immediate (vx)
        cdef uint32_t start = self.counter + 2
        cdef uint32_t end = start + lx
        cdef bytes vx_bytes = self.program.zeta[start:end]
        cdef uint64_t vx = chi(int.from_bytes(vx_bytes, "little"), lx)
        
        # Extract second immediate (vy)
        start = self.counter + 2 + lx
        end = start + ly
        cdef bytes vy_bytes = self.program.zeta[start:end]
        cdef uint64_t vy = chi(int.from_bytes(vy_bytes, "little"), ly)

        return [lx, ly, vx, vy]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            30: OpCode(name="store_imm_u8", fn=cls.store_imm_u8, gas=1, is_terminating=False),
            31: OpCode(name="store_imm_u16", fn=cls.store_imm_u16, gas=1, is_terminating=False),
            32: OpCode(name="store_imm_u32", fn=cls.store_imm_u32, gas=1, is_terminating=False),
            33: OpCode(name="store_imm_u64", fn=cls.store_imm_u64, gas=1, is_terminating=False),
        }

    cdef tuple  store_imm_u8(self, uint64_t *registers, CyMemory memory, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC30: Store immediate 8-bit value."""
        cdef uint8_t value = <uint8_t>(vy % 2**8)
        cdef uint64_t address = <uint64_t>vx
        memory.write(address & 0xFFFFFFFF, value.to_bytes(1, 'little'))
        return CONTINUE, -1

    cdef tuple  store_imm_u16(self, uint64_t *registers, CyMemory memory, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC31: Store immediate 16-bit value."""
        cdef uint16_t value = <uint16_t>(vy % 2**16)
        cdef uint64_t address = <uint64_t>vx
        memory.write(address & 0xFFFFFFFF, value.to_bytes(2, 'little'))
        return CONTINUE, -1

    cdef tuple  store_imm_u32(self, uint64_t *registers, CyMemory memory, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC32: Store immediate 32-bit value."""
        cdef uint32_t value = <uint32_t>(vy % 2**32)
        cdef uint64_t address = <uint64_t>vx
        memory.write(address & 0xFFFFFFFF, value.to_bytes(4, 'little'))
        return CONTINUE, -1

    cdef tuple  store_imm_u64(self, uint64_t *registers, CyMemory memory, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC33: Store immediate 64-bit value."""
        cdef uint64_t value = <uint64_t>(vy % 2**64)
        cdef uint64_t address = <uint64_t>vx
        memory.write(address & 0xFFFFFFFF, value.to_bytes(8, 'little'))
        return CONTINUE, -1

