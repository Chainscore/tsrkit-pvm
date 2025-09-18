# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

from typing import List, Any
from libc.stdint cimport int64_t, int32_t, uint8_t, uint32_t, uint64_t
from ..common.status import CONTINUE
from .cy_memory cimport CyMemory 
from .cy_program cimport CyProgram
from .instructions.cy_table cimport CyTableEntry

cdef class CyCompiledInstruction:
    """Pre-compiled instruction with decoded operands and cached function pointers."""
    def __init__(self, opcode: int, next_pc: int, handler: CyTableEntry, vx: uint64_t, vy: uint64_t, ra: uint8_t, rb: uint8_t, rd: uint8_t):
        self.opcode = opcode
        self.next_pc = next_pc
        self.handler = handler
        self.vx = vx
        self.vy = vy
        self.ra = ra
        self.rb = rb
        self.rd = rd

cdef class CyBlockInfo:
    """Compiled basic block with pre-decoded instructions."""
    def __init__(self, total_gas: uint32_t, instructions: List):
        self.total_gas = total_gas
        self.instructions = instructions
    
    cdef tuple execute(self, CyProgram program, uint32_t start_pc, uint64_t *reg_arr, CyMemory memory):
        """Execute block with optimized loop."""
        cdef uint32_t current_pc = start_pc
        cdef uint32_t i
        cdef object status = CONTINUE
        cdef uint32_t next_pc
        cdef CyCompiledInstruction compiled_inst
        cdef CyTableEntry handler
        cdef tuple result
        
        # Pre-cache data to eliminate repeated attribute access
        instructions = self.instructions
        total_gas = self.total_gas
        
        for i in range(len(instructions)):
            compiled_inst = instructions[i]
            # All critical data is now pre-cached in CompiledInstruction
            handler = compiled_inst.handler
            
            print(f"Executing {compiled_inst.opcode}")
            result = handler.fn(
                program, reg_arr, memory, current_pc, 
                compiled_inst.vx, compiled_inst.vy, 
                compiled_inst.ra, compiled_inst.rb, compiled_inst.rd
            )
            
            status = result[0]
            next_pc = result[1]
            
            if next_pc == 0xFFFF_FFFF:
                next_pc = compiled_inst.next_pc
            
            # Use pre-cached termination flag
            if handler.is_terminating:
                print(">> EXIT <<")
                return (status, next_pc), total_gas
            else:
                # For non-terminating instructions, advance PC normally
                current_pc = compiled_inst.next_pc
                
        # Block completed normally (shouldn't happen as blocks end with terminating instructions)
        return (status, current_pc), total_gas

