# cython: language_level=3
# cython: boundscheck=False, wraparound=False, cdivision=True
from libc.stdint cimport uint8_t, int32_t, uint64_t

from .cy_memory  cimport CyMemory
from .cy_program cimport CyProgram
from .cy_block   cimport CyBlockInfo, CyCompiledInstruction
from .instructions.cy_table cimport CyTable, CyTableEntry, InstructionProps
from .cy_status cimport PVM_OUT_OF_GAS, PvmExit

# --- move all cimports to module level --------------------
from .instructions.tables.wo_args cimport InstructionsWoArgs as T0
from .instructions.tables.i_imm cimport CyInstructionsWArgs1Imm as T1
from .instructions.tables.i_offset cimport CyWArgsOneOffset as T2
from .instructions.tables.i_reg_i_ewimm cimport CyInstructionsWArgs1Reg1EwImm as T3
from .instructions.tables.i_reg_i_imm cimport CyInstructionsWArgs1Reg1Imm as T4
from .instructions.tables.i_reg_i_imm_i_offset cimport InstructionsWArgs1Reg1Imm1Offset as T5
from .instructions.tables.i_reg_ii_imm cimport CyInstructionsWArgs1Reg2Imm as T6
from .instructions.tables.ii_imm cimport CyInstructionsWArgs2Imm as T7
from .instructions.tables.ii_reg cimport CyInstructionsWArgs2Reg as T8
from .instructions.tables.ii_reg_i_imm cimport CyInstructionsWArgs2Reg1Imm as T9
from .instructions.tables.ii_reg_i_offset cimport CyInstructionsWArgs2Reg1Offset as TA
from .instructions.tables.ii_reg_ii_imm cimport CyInstructionsWArgs2Reg2Imm as TB
from .instructions.tables.iii_reg cimport CyInstructionsWArgs3Reg as TC
# ----------------------------------------------------------


cdef class CyInstMapper:
    """
    Cython optimized instruction mapper with direct opcode-to-handler dispatch table.
    """
    
    def __cinit__(self):
        for i in range(256):
            self._dispatch_table[i]  = <void*>0
            self._dispatch_opdata[i] = <void*>0
        self._keep_alive = []
        self._init_dispatch_table()
                    
    cdef void _init_dispatch_table(self):
        # create one Python object per concrete table
        cdef object tbl_obj
        cdef CyTable tbl
        table_objs = [T0(), T1(), T2(), T3(), T4(), T5(),
                      T6(), T7(), T8(), T9(), TA(), TB(), TC()]

        for tbl_obj in table_objs:
            self._keep_alive.append(tbl_obj)
            tbl = <CyTable>tbl_obj
            for opcode, ent in (<object>tbl).get_table().items():
                self._dispatch_table[opcode]  = <void*>tbl
                self._dispatch_opdata[opcode] = <void*>ent
                self._keep_alive.append(ent)
    
    cpdef bint is_terminating(self, uint8_t opcode):
        """Check if an opcode corresponds to a terminating instruction."""
        cdef CyTableEntry entry_ptr = <CyTableEntry>self._dispatch_opdata[opcode]
        return entry_ptr is not None and entry_ptr.is_terminating

    cpdef uint32_t get_gas_cost(self, uint8_t opcode):
        """Get the gas cost for an opcode."""
        cdef CyTableEntry entry_ptr = <CyTableEntry>self._dispatch_opdata[opcode]
        return 0 if entry_ptr is None else entry_ptr.gas_cost
    
    cdef tuple process_instruction(self, CyProgram program, int32_t program_counter, 
                                     uint64_t *registers, CyMemory memory):
        """
        Execute an instruction using the optimized dispatch table.
        """
        cdef CyBlockInfo block = self.get_block(program, program_counter)
        return block.execute(program, program_counter, registers, memory)
    
    cdef CyBlockInfo get_block(self, CyProgram program, int32_t start_pc):
        """Get compiled block from cache or compile new one."""
        block = program._exec_blocks.get(start_pc)
        if block:
            return block

        # Compile block and cache it
        block = self._compile_block(program, start_pc)
        program._exec_blocks[start_pc] = block
        return block
    
    cdef CyBlockInfo _compile_block(self, CyProgram program, int32_t start_pc):
        """Compile a basic block starting at the given PC with aggressive pre-caching."""
        cdef int32_t current_pc = start_pc
        cdef uint8_t opcode
        cdef CyTable table_instance
        cdef CyTableEntry entry
        cdef uint32_t total_gas = 0
        cdef InstructionProps props
        cdef uint64_t skip_index

        compiled_instructions = []
        
        while True:
            opcode = program.zeta[current_pc]
            table_instance = <CyTable>self._dispatch_table[opcode]
            
            entry = <CyTableEntry>self._dispatch_opdata[opcode]
            
            skip_index = program.skip(current_pc)

            # Get instruction arguments using the unified interface with C struct
            props = table_instance.get_props(current_pc, program, skip_index)
            vx, vy, ra, rb, rd = props.vx, props.vy, props.ra, props.rb, props.rd

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
        
        return CyBlockInfo(total_gas, compiled_instructions)

# Global instance for compatibility with Python version
cdef public CyInstMapper inst_map = CyInstMapper()
