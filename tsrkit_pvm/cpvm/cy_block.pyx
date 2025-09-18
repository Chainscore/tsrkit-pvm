# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

from typing import List, Any
from libc.stdint cimport int64_t, int32_t, uint8_t, uint32_t, uint64_t
from ..common.status import CONTINUE
from .cy_memory import CyMemory 
from .cy_program import CyProgram

class CyCompiledInstruction:
    """Pre-compiled instruction with decoded operands and cached function pointers."""
    def __init__(self, opcode: int, offset: int, handler, args: List[int], table):
        self.opcode = opcode
        self.offset = offset
        self.handler = handler
        self.args = args
        self.table = table
        self.fn = handler.fn
        self.is_terminating = handler.is_terminating

cdef class CyBlockInfo:
    """Compiled basic block with pre-decoded instructions."""
    def __init__(self, end_pc: int, total_gas: uint32_t, instructions: List, instruction_count: int):
        self.end_pc = end_pc
        self.total_gas = total_gas
        self.instructions = instructions
        self.instruction_count = instruction_count
    
    cdef tuple execute(self, CyProgram program, int start_pc, uint64_t *reg_arr, CyMemory memory):
        """Execute block with optimized loop."""
        cdef int32_t current_pc = start_pc
        cdef int32_t i
        cdef object status = CONTINUE
        cdef int32_t next_pc
        
        # Pre-cache data to eliminate repeated attribute access
        instructions = self.instructions
        total_gas = self.total_gas
        
        for i, compiled_inst in enumerate(instructions):
            # All critical data is now pre-cached in CompiledInstruction
            status, next_pc = compiled_inst.fn(
                compiled_inst.table, reg_arr, memory, *compiled_inst.args
            )
            
            # Use pre-cached termination flag
            if compiled_inst.is_terminating:
                return (status, next_pc), total_gas
                
            if status != CONTINUE:
                return (status, next_pc), i + 1
            
            # For non-terminating instructions, advance PC normally
            current_pc = next_pc
                
        # Block completed normally (shouldn't happen as blocks end with terminating instructions)
        return (status, current_pc), total_gas

