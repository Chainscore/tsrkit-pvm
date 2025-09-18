# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 2 register + 2 immediate argument instructions.

This table handles instructions with complex argument parsing:
2 registers and 2 immediate values with varying bit layouts.
"""

from libc.stdint cimport uint32_t, int64_t, uint64_t, uint8_t
from tsrkit_pvm.common.status import CONTINUE, PANIC
from tsrkit_pvm.common.utils import chi, clamp_12, clamp_4, clamp_4_max0
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram
from math import floor

cdef tuple load_imm_jump_ind_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC180: Load immediate value into register and jump indirect."""
    wb = registers[rb]
    registers[ra] = vx
    status, target_counter = program.djump(counter, floor(wb + vy) % 2**32)
    return status, target_counter

cdef class CyInstructionsWArgs2Reg2Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 2 register + 2 immediate arguments.
    """
    
    cpdef tuple get_props(self, uint32_t program_counter, CyProgram program):
        """
        Extract two registers and two immediate arguments from program bytes.
        Returns (vx, vy, ra, rb, rd) where vx/vy are immediates, ra/rb are registers, rd is 0.
        """
        cdef uint32_t skip_index = program.skip(program_counter)
        cdef bytes zeta_slice = program.zeta[program_counter + 1:program_counter + 8]
        cdef uint32_t byte1_val = zeta_slice[0]
        cdef uint32_t byte2_val = zeta_slice[1] if len(zeta_slice) > 1 else 0
        
        # Parse registers from first byte
        cdef uint8_t ra = clamp_12(byte1_val & 0x0F)         # Lower 4 bits
        cdef uint8_t rb = clamp_12((byte1_val >> 4) & 0x0F)  # Upper 4 bits
        
        # Parse immediate lengths from second byte  
        cdef uint32_t lx = clamp_4(byte2_val & 0x07)          # Lower 3 bits
        cdef uint32_t ly = clamp_4((byte2_val >> 3) & 0x07)   # Next 3 bits
        
        # Clamp ly based on available space
        ly = clamp_4_max0(int(skip_index) - lx - 2)
        
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
        
        # Return in unified format: (vx, vy, ra, rb, rd)
        return (vx, vy, ra, rb, 0)

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = load_imm_jump_ind_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[180] = _e


