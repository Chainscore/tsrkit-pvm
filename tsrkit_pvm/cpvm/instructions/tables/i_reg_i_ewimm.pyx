# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

"""
Cython optimized i_reg_i_ewimm instruction table.
Instructions with 1 register + 1 extended width immediate argument (opcode 20).
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import clamp_12
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

# Unified dispatch function for load_imm_64 instruction
cdef tuple load_imm_64_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """
    OPC20: Load 64-bit immediate value into register.
    
    Args:
        program: Current program state
        registers: Register array
        memory: Memory object
        counter: Current program counter
        vx: 64-bit immediate value to load
        vy, rb, rd: Unused for this instruction
        ra: Target register index
        
    Returns:
        Tuple of (execution_status, next_pc)
    """
    registers[ra] = vx
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef class CyInstructionsWArgs1Reg1EwImm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 register + 1 extended width immediate argument.
    """
    
    cpdef tuple get_props(self, uint32_t program_counter, CyProgram program):
        """
        Extract register and 64-bit immediate arguments from program bytes.
        Returns (vx, vy, ra, rb, rd) where vx is the 64-bit immediate value, ra is register index, others are 0.
        """
        # Extract 9 bytes: 1 for register + 8 for 64-bit immediate
        cdef bytes zeta_slice = program.zeta[program_counter + 1: program_counter + 10]
        cdef uint8_t ra = clamp_12(zeta_slice[0] % 16)
        cdef bytes vx_bytes = bytes(zeta_slice[1:9])
        cdef uint64_t vx = int.from_bytes(vx_bytes, "little")
        
        # Return in unified format: (vx, vy, ra, rb, rd)
        return (vx, 0, ra, 0, 0)

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = load_imm_64_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[20] = _e

