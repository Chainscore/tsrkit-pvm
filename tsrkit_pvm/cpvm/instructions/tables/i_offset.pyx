# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 1 offset argument instructions.

This table handles instructions that take a single offset argument:
- jump: Unconditional jump instruction
"""

from typing import Dict
from libc.stdint cimport uint32_t, uint64_t
from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import clamp_4, z
from tsrkit_pvm.core.opcode import OpCode

cdef class CyWArgsOneOffset:
    """
    Cython optimized instruction table for 1 offset argument instructions.
    
    This class provides high-performance implementations of instructions that
    take a single offset argument, optimized with Cython for speed.
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
        Extract the offset argument from the instruction stream.
        Returns [lx, vx] where lx is length and vx is the computed offset.
        """
        cdef uint32_t lx = clamp_4(self.skip_index)
        cdef uint32_t start = self.counter + 1
        cdef uint32_t end = start + lx
        cdef bytes offset_bytes = self.program.zeta[start:end]
        cdef uint32_t raw_offset = int.from_bytes(offset_bytes, "little")
        cdef uint64_t vx = int(self.counter) + z(raw_offset, lx)
        return [vx]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            40: OpCode(name="jump", fn=cls.jump, gas=1, is_terminating=True),
        }

    cpdef tuple jump(self, list registers, object memory, uint64_t vx):
        """
        OPC40: Unconditional jump to specified offset.
        
        Args:
            registers: Register array 
            memory: Memory object
            vx: Target jump address
        
        Returns:
            Tuple of (status, next_pc, registers, memory)
        """
        # Use the program's branch method for proper jump validation
        cdef object status_result = self.program.branch(self.counter, vx, True)
        cdef object status = status_result[0]
        cdef uint32_t target_counter = status_result[1]
        
        if status == CONTINUE and target_counter != self.counter:
            return status, target_counter, registers, memory
        
        # Default fallthrough
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory


