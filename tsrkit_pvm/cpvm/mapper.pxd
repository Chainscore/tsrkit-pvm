# cython: language_level=3

"""
Cython header file for the instruction mapper.
This allows other Cython modules to cimport and use the CyInstMapper class efficiently.
"""

from libc.stdint cimport int32_t, uint32_t, uint64_t, uint8_t
from .cy_program cimport CyProgram
from .cy_memory cimport CyMemory
from .instructions.cy_table cimport CyTableEntry
from .cy_block cimport CyBlockInfo, CyCompiledInstruction

cdef class CyInstMapper:
    """
    Cython optimized instruction mapper with direct opcode-to-handler dispatch table.
    """
    
    cdef public list _dispatch_table  # 256-entry list of [Table class, CyTableEntry]
    cdef public dict _basic_blocks     # Cache for compiled blocks

    cdef void _init_dispatch_table(self)
    
    cpdef bint is_terminating(self, uint8_t opcode)
    cpdef uint32_t get_gas_cost(self, uint8_t opcode)
    
    cdef tuple process_instruction(self, CyProgram program, int32_t program_counter, 
                                   uint64_t *registers, CyMemory memory)
    
    cdef CyBlockInfo get_block(self, CyProgram program, int32_t start_pc)

    cdef CyBlockInfo _compile_block(self, CyProgram program, int32_t start_pc)

# Global instance declaration
cdef CyInstMapper inst_map