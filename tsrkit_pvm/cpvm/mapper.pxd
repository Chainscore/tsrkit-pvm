# cython: language_level=3
from libc.stdint cimport uint8_t, int32_t, uint32_t, uint64_t
from .cy_program  cimport CyProgram
from .cy_memory   cimport CyMemory
from .cy_block    cimport CyBlockInfo
from .instructions.cy_table cimport CyTable, CyTableEntry, InstructionProps

cdef class CyInstMapper:
    # C arrays holding void* (no Python lookup at runtime)
    cdef void* _dispatch_table[256]
    cdef void* _dispatch_opdata[256]

    cdef list _keep_alive                # only for GC safety

    cdef void _init_dispatch_table(self)

    cpdef bint     is_terminating(self, uint8_t opcode)
    cpdef uint32_t get_gas_cost(self, uint8_t opcode)

    cdef tuple process_instruction(self,
                                   CyProgram  program,
                                   int32_t    pc,
                                   uint64_t*  registers,
                                   CyMemory   memory)

    cdef CyBlockInfo get_block(self, CyProgram program, int32_t start_pc)
    cdef CyBlockInfo _compile_block(self, CyProgram program, int32_t start_pc)

cdef CyInstMapper inst_map