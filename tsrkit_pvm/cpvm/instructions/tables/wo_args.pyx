# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

from typing import Dict
from libc.stdint cimport uint32_t

from tsrkit_pvm.common.status import CONTINUE, PANIC, PvmError
from tsrkit_pvm.core.instruction_table import InstructionTable
from tsrkit_pvm.core.opcode import OpCode, OpReturn

    
cdef class InstructionsWoArgs:
    cdef uint32_t counter
    cdef object program
    cdef uint32_t skip_index

    def __init__(self, uint32_t counter, object program, uint32_t skip_index):
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    cpdef list get_props(self):
        return []

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            0: OpCode(name="trap", fn=cls.trap, gas=1, is_terminating=True),
            1: OpCode(name="fallthrough", fn=cls.fallthrough, gas=1, is_terminating=True),
        }

    cpdef tuple trap(self, list registers, object memory):
        raise PvmError(PANIC)

    cpdef tuple fallthrough(self, list registers, object memory):
        cdef uint32_t next_pc = self.counter + self.skip_index + 1
        return CONTINUE, next_pc, registers, memory


