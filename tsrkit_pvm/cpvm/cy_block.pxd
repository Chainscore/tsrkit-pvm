# cython: language_level=3

"""
Cython declaration file for cy_block.pyx

This file exposes the CyCompiledInstruction and CyBlockInfo classes 
for efficient block compilation and execution.
"""
from libc.stdint cimport int32_t, uint32_t, uint64_t, uint8_t
from .cy_program cimport CyProgram
from .cy_memory cimport CyMemory

# Define an instruction function pointer type:
# returns an `int` status, and writes `next_pc` into the out pointer.
ctypedef int (*instr_fn_t)(uint64_t *registers,
                           CyMemory memory,
                           uint64_t vx,
                           uint64_t vy,
                           uint8_t ra,
                           uint8_t rb, 
                           uint8_t rc)


cdef class CyCompiledInstruction:
    """Pre-compiled instruction with decoded operands and cached function pointers."""
    
    # Public attributes
    cdef public int             opcode
    cdef public int             offset
    cdef public object          handler
    cdef public list            args
    cdef public object          table
    cdef instr_fn_t             fn
    cdef public bint            is_terminating

cdef class CyBlockInfo:
    """Compiled basic block with pre-decoded instructions."""
    
    # Public attributes
    cdef public int           end_pc
    cdef public uint32_t      total_gas
    cdef public list          instructions
    cdef public int           instruction_count
    
    # Methods
    cdef tuple execute(self, CyProgram program, int start_pc, uint64_t *reg_arr, CyMemory memory)