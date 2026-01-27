# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=False
# cython: linetrace=False
# cython: nonecheck=False
# cython: initializedcheck=False
# cython: overflowcheck=False
# cython: infer_types=True
# cython: optimize.unpack_method_calls=True

from typing import List, Any
from libc.stdint cimport int64_t, int32_t, uint8_t, uint32_t, uint64_t
from libc.time cimport time_t, clock, CLOCKS_PER_SEC
import time
from .cy_status cimport CONTINUE, PVM_CONTINUE, CyStatus, PvmExit
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
        """Execute block with optimized loop - minimal Python object creation."""
        cdef uint32_t current_pc = start_pc
        cdef uint32_t i
        cdef uint32_t next_pc
        cdef CyCompiledInstruction compiled_inst
        cdef CyTableEntry handler
        cdef tuple result
        
        # Pre-cache the list and size to avoid repeated attribute lookups
        cdef list instructions = self.instructions
        cdef uint32_t instructions_size = len(instructions)
        cdef uint32_t total_gas = self.total_gas
        
        # Execute instructions with minimal overhead
        for i in range(instructions_size):
            compiled_inst = instructions[i]
            handler = compiled_inst.handler
            
            # print(i, "🚨" if handler.is_terminating else "✅", "opcode:", compiled_inst.opcode, "at PC:", current_pc)

            # Call the instruction function directly
            try:
                next_pc = handler.fn(
                    program, reg_arr, memory, current_pc, 
                    compiled_inst.vx, compiled_inst.vy, 
                    compiled_inst.ra, compiled_inst.rb, compiled_inst.rd
                )
            except PvmExit as e:
                e.next_pc = compiled_inst.next_pc
                e.gas_cost = i + 1
                raise e

            if next_pc == 0xFFFF_FFFF:
                next_pc = compiled_inst.next_pc

            # print("-> Next PC:", next_pc)

            # Use pre-cached termination flag
            if handler.is_terminating:
                # print("🏁 Block terminated at PC:", current_pc, "with opcode:", compiled_inst.opcode)
                return next_pc, total_gas

            # For non-terminating instructions, advance PC normally
            current_pc = next_pc
                
        # Block completed normally (shouldn't happen as blocks end with terminating instructions)
        print("⚠️ Block ended without termination instruction")
        return current_pc, total_gas
