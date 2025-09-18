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
from .instructions.cy_table cimport CyTable, CyTableEntry, instr_fn_t

# --- move all cimports to module level --------------------
from .instructions.tables.wo_args cimport InstructionsWoArgs
from .instructions.tables.i_imm cimport CyInstructionsWArgs1Imm
from .instructions.tables.i_offset cimport CyWArgsOneOffset
from .instructions.tables.i_reg_i_ewimm cimport CyInstructionsWArgs1Reg1EwImm
from .instructions.tables.i_reg_i_imm cimport CyInstructionsWArgs1Reg1Imm
from .instructions.tables.i_reg_i_imm_i_offset cimport InstructionsWArgs1Reg1Imm1Offset
from .instructions.tables.i_reg_ii_imm cimport CyInstructionsWArgs1Reg2Imm
from .instructions.tables.ii_imm cimport CyInstructionsWArgs2Imm
from .instructions.tables.ii_reg cimport CyInstructionsWArgs2Reg
from .instructions.tables.ii_reg_i_imm cimport CyInstructionsWArgs2Reg1Imm
from .instructions.tables.ii_reg_i_offset cimport CyInstructionsWArgs2Reg1Offset
from .instructions.tables.ii_reg_ii_imm cimport CyInstructionsWArgs2Reg2Imm
from .instructions.tables.iii_reg cimport CyInstructionsWArgs3Reg
# ----------------------------------------------------------

cdef class CyInstMapper:
    """
    Cython optimized instruction mapper with direct opcode-to-handler dispatch table.
    """
    
    def __init__(self):
        self._dispatch_table = [None] * 256
        self._basic_blocks = {}
        self._init_dispatch_table()
                    
    cdef void _init_dispatch_table(self):
        """Initialize the dispatch table with all instruction tables."""
        # Map tables to their classes using get_table() instance methods
        cdef list table_mappings = [
            (InstructionsWoArgs().get_table(), InstructionsWoArgs),
            (CyInstructionsWArgs1Imm().get_table(), CyInstructionsWArgs1Imm),
            (CyWArgsOneOffset().get_table(), CyWArgsOneOffset),
            (CyInstructionsWArgs1Reg1EwImm().get_table(), CyInstructionsWArgs1Reg1EwImm),
            (CyInstructionsWArgs1Reg1Imm().get_table(), CyInstructionsWArgs1Reg1Imm),
            (InstructionsWArgs1Reg1Imm1Offset().get_table(), InstructionsWArgs1Reg1Imm1Offset),
            (CyInstructionsWArgs1Reg2Imm().get_table(), CyInstructionsWArgs1Reg2Imm),
            (CyInstructionsWArgs2Imm().get_table(), CyInstructionsWArgs2Imm),
            (CyInstructionsWArgs2Reg().get_table(), CyInstructionsWArgs2Reg),
            (CyInstructionsWArgs2Reg1Imm().get_table(), CyInstructionsWArgs2Reg1Imm),
            (CyInstructionsWArgs2Reg1Offset().get_table(), CyInstructionsWArgs2Reg1Offset),
            (CyInstructionsWArgs2Reg2Imm().get_table(), CyInstructionsWArgs2Reg2Imm),
            (CyInstructionsWArgs3Reg().get_table(), CyInstructionsWArgs3Reg),
        ]
        
        # Populate dispatch table
        for table_dict, table_class in table_mappings:
            for opcode, entry in table_dict.items():
                self._dispatch_table[opcode] = [table_class, entry]
    
    cpdef bint is_terminating(self, uint8_t opcode):
        """Check if an opcode corresponds to a terminating instruction."""
        cdef list handler_entry = self._dispatch_table[opcode]
        if handler_entry is None:
            return False  # Unknown opcodes are not terminating
        cdef CyTableEntry entry = handler_entry[1]
        return entry.is_terminating
    
    cpdef uint32_t get_gas_cost(self, uint8_t opcode):
        """Get the gas cost for an opcode."""
        cdef list handler_entry = self._dispatch_table[opcode]
        if handler_entry is None:
            return 0  # Unknown opcodes have no gas cost
        cdef CyTableEntry entry = handler_entry[1]
        return entry.gas_cost
    
    cdef tuple process_instruction(self, CyProgram program, int32_t program_counter, 
                                   uint64_t *registers, CyMemory memory):
        """
        Execute an instruction using the optimized dispatch table.
        """
        cdef CyBlockInfo block = self.get_block(program, program_counter)
        return block.execute(program, program_counter, registers, memory)
    
    cdef CyBlockInfo get_block(self, CyProgram program, int32_t start_pc):
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
        cdef list handler_entry
        cdef object table_class
        cdef CyTableEntry entry
        cdef uint32_t total_gas = 0
        cdef tuple props
        
        compiled_instructions = []
        
        while True:
            opcode = program.zeta[current_pc]
            handler_entry = self._dispatch_table[opcode]
            
            if handler_entry is None:
                raise ValueError(f"Invalid opcode: {opcode} at PC {current_pc}")
            
            table_class, entry = handler_entry
            
            # Get instruction arguments using the unified interface
            props = table_class().get_props(current_pc, program)
            vx, vy, ra, rb, rd = props[0], props[1], props[2], props[3], props[4]
        
            skip_index = program.skip(current_pc)

            next_pc = current_pc + skip_index + 1
            # Create compiled instruction with pre-cached function and flags
            compiled_inst = CyCompiledInstruction(
                opcode,
                next_pc,
                entry,
                vx, vy, ra, rb, rd,
            )
            
            compiled_instructions.append(compiled_inst)
            total_gas += entry.gas_cost
            
            # Stop at terminating instructions
            if entry.is_terminating:
                break

            # Move to next instruction
            current_pc = next_pc
                
        return CyBlockInfo(
            total_gas=total_gas,
            instructions=compiled_instructions,
        )

# Global instance for compatibility with Python version
cdef public CyInstMapper inst_map = CyInstMapper()
