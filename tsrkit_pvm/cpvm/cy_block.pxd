# cython: language_level=3

"""
Cython declaration file for cy_block.pyx

This file exposes the CyCompiledInstruction and CyBlockInfo classes 
for efficient block compilation and execution.
"""
from libc.stdint cimport int32_t, uint32_t, uint64_t, uint8_t
from .cy_program cimport CyProgram
from .cy_memory cimport CyMemory
from .instructions.cy_table cimport CyTableEntry, instr_fn_t


cdef class CyCompiledInstruction:
    """Pre-compiled instruction with decoded operands and cached function pointers."""
    
    # Public attributes
    cdef public int             opcode
    cdef public uint32_t        next_pc
    cdef public CyTableEntry    handler

    cdef public uint64_t        vx
    cdef public uint64_t        vy
    cdef public uint8_t         ra
    cdef public uint8_t         rb 
    cdef public uint8_t         rd

cdef class CyBlockInfo:
    """Compiled basic block with pre-decoded instructions."""
    
    # Public attributes
    cdef public uint32_t      total_gas
    cdef public list          instructions
    
    # Methods
    cdef tuple execute(self, CyProgram program, uint32_t start_pc, uint64_t *reg_arr, CyMemory memory)