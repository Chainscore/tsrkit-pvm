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

from tsrkit_pvm.gas.props import (
    MEMORY_ACCESS_CYCLES,
    TRAP_OPCODE,
    UNLIKELY_OPCODE,
    get_destination_registers,
    get_source_registers,
)
from tsrkit_pvm.gas.simulator import compute_basic_block_gas
from tsrkit_pvm.interpreter.instructions.inst_map import inst_map as py_inst_map


cdef list _gas_args_from_props(uint8_t opcode, InstructionProps props):
    if opcode == 20:
        return [props.rd]
    if 50 <= opcode <= 62:
        return [props.ra]
    if 70 <= opcode <= 73:
        return [props.ra]
    if 80 <= opcode <= 90:
        return [props.ra, 0, 0, props.vx, props.vy]
    if 100 <= opcode <= 110:
        return [props.rd, props.ra]
    if 120 <= opcode <= 161:
        return [props.ra, props.rb]
    if 170 <= opcode <= 175:
        return [props.ra, props.rb, 0, props.vx]
    if opcode == 180:
        return [props.ra, props.rb]
    if 190 <= opcode <= 230:
        return [props.ra, props.rb, props.rd]
    return []


cdef object _resolve_cython_gas_profile(CyProgram program, int32_t pc, uint8_t opcode, list args):
    cdef uint32_t fallthrough
    cdef uint32_t target
    handler = py_inst_map._dispatch_table[opcode]
    if handler is None:
        raise ValueError(f"Invalid opcode {opcode} at PC {pc}")

    profile = handler.op_data.gas_profile
    source_registers = get_source_registers(opcode, args)
    destination_registers = get_destination_registers(opcode, args)

    execution_cycles = profile.execution_cycles
    if execution_cycles == "memory":
        execution_cycles = MEMORY_ACCESS_CYCLES
    elif execution_cycles == "branch":
        fallthrough = <uint32_t>(pc + 1 + program.skip(pc))
        if 81 <= opcode <= 90:
            target = <uint32_t>args[4]
        elif 170 <= opcode <= 175:
            target = <uint32_t>args[3]
        else:
            raise ValueError(f"Opcode {opcode} does not use branch gas")
        fallthrough_opcode = program.zeta[fallthrough] if fallthrough < program.zeta_len else TRAP_OPCODE
        target_opcode = program.zeta[target] if target < program.zeta_len else TRAP_OPCODE
        if fallthrough_opcode in (TRAP_OPCODE, UNLIKELY_OPCODE) or target_opcode in (TRAP_OPCODE, UNLIKELY_OPCODE):
            execution_cycles = 1
        else:
            execution_cycles = 20

    decode_slots = profile.decode_slots
    if not isinstance(decode_slots, int):
        kind, first, second = decode_slots
        if kind == "P":
            decode_slots = first if set(source_registers) & set(destination_registers) else second
        elif kind == "PS":
            decode_slots = first if source_registers and destination_registers and source_registers[0] == destination_registers[0] else second
        else:
            raise ValueError(f"Unknown decode slot rule: {decode_slots!r}")

    return (
        pc,
        opcode,
        execution_cycles,
        decode_slots,
        profile.units,
        source_registers,
        destination_registers,
    )


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

    cdef tuple process_instruction(self, CyProgram program, int32_t program_counter, 
                                     uint64_t *registers, CyMemory memory):
        """
        Execute an instruction using the optimized dispatch table.
        """
        cdef int32_t block_start = program.containing_basic_block_start(program_counter)
        cdef CyBlockInfo block = self.get_block(program, block_start)
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
        cdef InstructionProps props
        cdef uint64_t skip_index

        compiled_instructions = []
        gas_instructions = []
        
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
                current_pc,
                opcode,
                next_pc,
                entry,
                vx, vy, ra, rb, rd,
            )
            
            compiled_instructions.append(compiled_inst)
            gas_instructions.append(
                _resolve_cython_gas_profile(
                    program,
                    current_pc,
                    opcode,
                    _gas_args_from_props(opcode, props),
                )
            )
            
            # Stop at terminating instructions
            if entry.is_terminating:
                break

            # Move to next instruction
            current_pc = next_pc
        
        return CyBlockInfo(start_pc, compute_basic_block_gas(gas_instructions), compiled_instructions)

# Global instance for compatibility with Python version
cdef public CyInstMapper inst_map = CyInstMapper()
