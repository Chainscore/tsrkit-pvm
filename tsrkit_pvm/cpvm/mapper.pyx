# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

from typing import List, Any
from libc.stdint cimport int64_t, int32_t, uint8_t, uint32_t, uint64_t
from libc.string cimport memset
from cpython.mem cimport PyMem_Malloc, PyMem_Free
from ..common.status import CONTINUE
from .cy_memory cimport CyMemory 
from .cy_program cimport CyProgram

from .instructions.tables.i_imm import CyInstructionsWArgs1Imm
from .instructions.tables.wo_args import InstructionsWoArgs
from .instructions.tables.i_offset import CyWArgsOneOffset
from .instructions.tables.i_reg_i_ewimm import CyInstructionsWArgs1Reg1EwImm
from .instructions.tables.i_reg_i_imm import CyInstructionsWArgs1Reg1Imm
from .instructions.tables.i_reg_i_imm_i_offset import InstructionsWArgs1Reg1Imm1Offset
from .instructions.tables.i_reg_ii_imm import CyInstructionsWArgs1Reg2Imm
from .instructions.tables.ii_imm import CyInstructionsWArgs2Imm
from .instructions.tables.ii_reg import CyInstructionsWArgs2Reg
from .instructions.tables.ii_reg_i_imm import CyInstructionsWArgs2Reg1Imm
from .instructions.tables.ii_reg_i_offset import CyInstructionsWArgs2Reg1Offset
from .instructions.tables.ii_reg_ii_imm import CyInstructionsWArgs2Reg2Imm
from .instructions.tables.iii_reg import CyInstructionsWArgs3Reg
from .cy_block cimport CyBlockInfo, CyCompiledInstruction


all_tables = [
    InstructionsWoArgs,
    CyInstructionsWArgs1Imm,
    CyWArgsOneOffset,
    CyInstructionsWArgs1Reg1EwImm,
    CyInstructionsWArgs1Reg1Imm,
    InstructionsWArgs1Reg1Imm1Offset,
    CyInstructionsWArgs1Reg2Imm,
    CyInstructionsWArgs2Imm,
    CyInstructionsWArgs2Reg,
    CyInstructionsWArgs2Reg1Imm,
    CyInstructionsWArgs2Reg1Offset,
    CyInstructionsWArgs2Reg2Imm,
    CyInstructionsWArgs3Reg,
]

cdef struct COpInfo:
    uint8_t gas_cost
    uint8_t is_terminating

cdef class CyInstructionHandler:
    """Cython optimized instruction handler."""
    cdef public str name
    cdef public object fn
    cdef public int gas_cost
    cdef public bint is_terminating
    cdef public object table_class
    
    def __init__(self, str name, object fn, int gas_cost, bint is_terminating, object table_class):
        self.name = name
        self.fn = fn
        self.gas_cost = gas_cost
        self.is_terminating = is_terminating
        self.table_class = table_class

cdef class CyInstMapper:
    """
    Cython optimized instruction mapper with direct opcode-to-handler dispatch table.
    """
    cdef COpInfo* _op_info_table
    cdef uint64_t _terminating_mask
    cdef dict _basic_blocks
    cdef public list _dispatch_table  # 256-entry list of CyInstructionHandler
    cdef list _all_tables

    def __init__(self, all_tables: List[type]):
        self._all_tables = all_tables
        self._basic_blocks = {}
        self._dispatch_table = [None] * 256

        # Allocate C arrays for opcode info only
        self._op_info_table = <COpInfo*>PyMem_Malloc(256 * sizeof(COpInfo))
        if not self._op_info_table:
            raise MemoryError("Failed to allocate opcode info table")
        memset(self._op_info_table, 0, 256 * sizeof(COpInfo))
        self._terminating_mask = 0
        self._build_dispatch_table()
    
    def __dealloc__(self):
        """Clean up allocated memory."""
        if self._op_info_table:
            PyMem_Free(self._op_info_table)
    
    cdef void _build_dispatch_table(self):
        cdef int32_t opcode
        cdef COpInfo* op_info
        for table_class in self._all_tables:
            instruction_table = table_class.table()
            for opcode, op_code in instruction_table.items():
                if 0 <= opcode < 256:
                    op_info = &self._op_info_table[opcode]
                    op_info.gas_cost = op_code.gas
                    op_info.is_terminating = 1 if op_code.is_terminating else 0
                    self._dispatch_table[opcode] = CyInstructionHandler(
                        op_code.name, op_code.fn, op_code.gas, op_code.is_terminating, table_class
                    )
                    if op_code.is_terminating:
                        self._terminating_mask |= (1UL << opcode)
    
    cdef tuple process_instruction(self, CyProgram program, int32_t program_counter, 
                                   uint64_t *registers, CyMemory memory):
        """
        Execute an instruction using the optimized dispatch table.
        """
        cdef CyBlockInfo block = self.get_block(program, program_counter)
        return block.execute(program, program_counter, registers, memory)
    
    cpdef int32_t get_gas_cost(self, int32_t opcode):
        """Get gas cost with direct C array lookup."""
        if 0 <= opcode < 256:
            return self._op_info_table[opcode].gas_cost
        return 0
    
    cpdef bint is_terminating(self, int32_t opcode):
        """Check if instruction is terminating with bitwise operation."""
        if 0 <= opcode < 256:
            return bool((self._terminating_mask >> opcode) & 1)
        return False
    
    cpdef CyBlockInfo get_block(self, object program, int32_t start_pc):
        """Get compiled block from cache or compile new one."""
        if start_pc in self._basic_blocks:
            return self._basic_blocks[start_pc]
        
        # Compile block and cache it
        block = self._compile_block(program, start_pc)
        self._basic_blocks[start_pc] = block
        return block
    
    cdef CyBlockInfo _compile_block(self, CyProgram program, int32_t start_pc):
        """Compile a basic block starting at the given PC with aggressive pre-caching."""
        cdef int32_t current_pc = start_pc
        cdef uint8_t opcode
        cdef CyInstructionHandler handler
        cdef uint32_t total_gas = 0
        
        compiled_instructions = []
        
        while True:
            opcode = program.zeta[current_pc]
            handler = self._dispatch_table[opcode]
            
            if handler is None:
                raise ValueError(f"Invalid opcode: {opcode} at PC {current_pc}")
            
            # Create temporary table instance to get instruction arguments
            skip_count = program.skip(current_pc)
            table_instance = handler.table_class(counter=current_pc, program=program, skip_index=skip_count)
            args = table_instance.get_props()
            
            # Create compiled instruction with pre-cached function and flags
            compiled_inst = CyCompiledInstruction(
                opcode=opcode,
                offset=current_pc - start_pc,
                handler=handler,
                args=args,
                table=table_instance,
            )
            
            compiled_instructions.append(compiled_inst)
            total_gas += handler.gas_cost
            
            # Stop at terminating instructions
            if handler.is_terminating:
                break
                
            # Move to next instruction
            current_pc += 1 + skip_count
        
        return CyBlockInfo(
            end_pc=current_pc,
            total_gas=total_gas,
            instructions=compiled_instructions,
            instruction_count=len(compiled_instructions)
        )

# Global instance for compatibility with Python version
inst_map = CyInstMapper(all_tables)
