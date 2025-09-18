# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

"""
Cython optimized wo_args instruction table.
Instructions without arguments (opcodes 0-9).
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from tsrkit_pvm.common.status import PvmError, CONTINUE, PANIC
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

# Separate dispatch functions for instructions

cdef tuple trap_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """
    OPC0: Trap - Raise panic error.
    All arguments unused for this instruction.
    
    Returns:
        Tuple of (PANIC, next_pc)
    """
    # Trap instruction causes panic and terminates execution
    return (PANIC, <uint32_t>0xFFFFFFFF)

cdef tuple fallthrough_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """
    OPC1: Fallthrough - Continue execution.
    All arguments unused for this instruction.
    
    Returns:
        Tuple of (CONTINUE, next_pc)
    """
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef class InstructionsWoArgs(CyTable):
    """
    Cython optimized instruction table for instructions without arguments.
    """
    
    cpdef tuple get_props(self, uint32_t program_counter, CyProgram program):
        """
        No arguments to extract for these instructions.
        Returns (vx, vy, ra, rb, rd) all as 0.
        """
        return (0, 0, 0, 0, 0)
    
    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = trap_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[0] = _e
_e = CyTableEntry(); _e.fn = fallthrough_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[1] = _e


