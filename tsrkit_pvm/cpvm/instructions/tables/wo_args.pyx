# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

from typing import Dict
from libc.stdint cimport uint32_t, uint64_t
from tsrkit_pvm.common.status import PvmError, CONTINUE, PANIC
from tsrkit_pvm.core.opcode import OpCode, OpReturn
from ...cy_memory cimport CyMemory

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

    cdef tuple  trap(self, uint64_t *registers, CyMemory memory):
        raise PvmError(PANIC, -1, "Trap instruction executed")

    cdef tuple  fallthrough(self, uint64_t *registers, CyMemory memory):
        return CONTINUE, -1


