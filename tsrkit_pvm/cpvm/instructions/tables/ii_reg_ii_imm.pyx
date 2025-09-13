# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 2 register + 2 immediate argument instructions.

This table handles instructions with complex argument parsing:
2 registers and 2 immediate values with varying bit layouts.
"""

from typing import Dict
cimport cython
from libc.stdint cimport uint32_t, int64_t, uint64_t

from tsrkit_pvm.core.opcode import OpCode
from tsrkit_pvm.common.status import CONTINUE, PANIC
from tsrkit_pvm.common.utils import chi, clamp_12, clamp_4, clamp_4_max0

cdef class CyInstructionsWArgs2Reg2Imm:
    """Cython optimized instruction class for 2 register + 2 immediate instructions."""
    
    cdef public object program
    cdef public uint32_t counter
    cdef public uint32_t skip_index
    
    def __init__(self, counter, program, skip_index):
        self.counter = counter
        self.program = program  
        self.skip_index = skip_index

    cpdef list get_props(self):
        """Extract 2 register indices and 2 immediate values from the instruction."""
        cdef bytes zeta_slice = self.program.zeta[self.counter + 1:self.counter + 8]
        cdef uint32_t byte1_val = zeta_slice[0]
        cdef uint32_t byte2_val = zeta_slice[1] if len(zeta_slice) > 1 else 0
        
        # Parse registers from first byte
        cdef uint32_t ra = clamp_12(byte1_val & 0x0F)         # Lower 4 bits
        cdef uint32_t rb = clamp_12((byte1_val >> 4) & 0x0F)  # Upper 4 bits
        
        # Parse immediate lengths from second byte  
        cdef uint32_t lx = clamp_4(byte2_val & 0x07)          # Lower 3 bits
        cdef uint32_t ly = clamp_4((byte2_val >> 3) & 0x07)   # Next 3 bits
        
        # Clamp ly based on available space
        ly = clamp_4_max0(int(self.skip_index) - lx - 2)
        
        # Extract first immediate value
        cdef uint64_t vx = 0
        cdef bytes imm1_slice
        if lx > 0:
            imm1_slice = zeta_slice[2:2+lx]
            vx = chi(int.from_bytes(imm1_slice, "little"), lx)
        
        # Extract second immediate value  
        cdef uint64_t vy = 0
        cdef bytes imm2_slice
        if ly > 0:
            imm2_slice = zeta_slice[2+lx:2+lx+ly]
            vy = chi(int.from_bytes(imm2_slice, "little"), ly)
        
        return [ra, rb, lx, ly, vx, vy]


    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            180: OpCode(
                name="load_imm_jump_ind",
                fn=cls.load_imm_jump_ind,
                gas=1,
                is_terminating=True,
            ),
        }


    cpdef tuple load_imm_jump_ind(self, list registers, object memory, uint32_t ra, uint32_t rb, uint32_t lx, uint32_t ly, uint64_t vx, uint64_t vy):
        """OPC180: Load immediate value into register and jump indirect."""
        from math import floor
        wb = registers[rb]
        registers[ra] = vx
        status, counter = self.program.djump(self.counter, floor(wb + vy) % 2**32)
        return status, counter, registers, memory
