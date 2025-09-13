# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

"""
Cython optimized i_imm instruction table.
Instructions with 1 immediate argument (opcodes 10-19).
"""

from typing import Dict
from libc.stdint cimport uint32_t, uint64_t
from tsrkit_pvm.common.status import HOST
from tsrkit_pvm.common.utils import chi, clamp_4
from tsrkit_pvm.core.opcode import OpCode

cdef class CyInstructionsWArgs1Imm:
    """
    Cython optimized instruction table for instructions with 1 immediate argument.
    """
    cdef uint32_t counter
    cdef object program
    cdef uint32_t skip_index
    
    def __init__(self, uint32_t counter, object program, uint32_t skip_index):
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    cpdef list get_props(self):
        """
        Extract immediate value from program bytes.
        Returns [lx, vx] where lx is byte length and vx is the immediate value.
        """
        cdef uint32_t lx = clamp_4(self.skip_index)
        cdef uint32_t start = self.counter + 1
        cdef uint32_t end = start + lx
        
        # Extract bytes and convert to integer
        cdef bytes byte_slice = self.program.zeta[start:end]
        cdef uint64_t immediate_value = int.from_bytes(byte_slice, "little")
        
        # Apply chi transformation
        cdef uint64_t vx = chi(immediate_value, lx)
        
        return [lx, vx]
    
    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            10: OpCode(name="ecalli", fn=cls.ecalli, gas=1, is_terminating=False),
        }

    cpdef tuple ecalli(self, list registers, object memory, uint32_t lx, uint64_t vx):
        """
        OPC10: Ecalli - Execute call immediate.
        Performs a host call with the immediate value.
        
        Args:
            registers: Current register state
            memory: Current memory state  
            lx: Byte length of immediate
            vx: Immediate value to pass to host
            
        Returns:
            Tuple of (status, next_pc, registers, memory)
        """
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return HOST(vx), next_pc, registers, memory

