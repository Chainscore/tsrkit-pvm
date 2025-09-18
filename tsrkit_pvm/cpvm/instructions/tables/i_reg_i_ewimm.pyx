# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 1 register + 1 extended width immediate argument instructions.

This table handles instructions that take one register and one 64-bit immediate argument:
- load_imm_64: Load 64-bit immediate value into register
"""

from typing import Dict
cimport cython
from libc.stdint cimport uint32_t, uint64_t

from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import clamp_12
from tsrkit_pvm.core.opcode import OpCode
from ...cy_memory cimport CyMemory


cdef class CyInstructionsWArgs1Reg1EwImm:
    """
    Cython optimized instruction table for 1 register + 1 extended width immediate argument instructions.
    
    This class provides high-performance implementations of instructions that
    take one register and one 64-bit immediate argument, optimized with Cython for speed.
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
        Extract register and 64-bit immediate arguments from the instruction stream.
        Returns [ra, vx] where ra is register, vx is the 64-bit immediate value.
        """
        cdef bytes zeta_slice = self.program.zeta[self.counter + 1: self.counter + 10]
        cdef uint32_t ra = clamp_12(zeta_slice[0] % 16)
        cdef bytes vx_bytes = bytes(zeta_slice[1:9])
        cdef uint64_t vx = int.from_bytes(vx_bytes, "little")
        return [ra, vx]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            20: OpCode(name="load_imm_64", fn=cls.load_imm_64, gas=1, is_terminating=False),
        }

    cdef tuple load_imm_64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint64_t vx):
        """OPC20: Load 64-bit immediate value into register."""
        registers[ra] = vx
        return CONTINUE, -1
