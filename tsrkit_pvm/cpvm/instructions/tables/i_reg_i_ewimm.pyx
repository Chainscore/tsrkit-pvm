# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from ...cy_status cimport CONTINUE
from ...cy_utils cimport clamp_12
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

# Unified dispatch function for load_imm_64 instruction
cdef inline uint32_t load_imm_64_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """
    OPC20: Load 64-bit immediate value into register.
    
    Args:
        program: Current program state
        registers: Register array
        memory: Memory object
        counter: Current program counter
        vx: 64-bit immediate value to load
        vy, rb, rd: Unused for this instruction
        ra: Target register index
        
    Returns:
        Tuple of (execution_status, next_pc)
    """
    registers[ra] = vx
    return <uint32_t>0xFFFFFFFF

cdef class CyInstructionsWArgs1Reg1EwImm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 register + 1 extended width immediate argument.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract register and 64-bit immediate arguments from program bytes.
        Returns InstructionProps struct where vx is the 64-bit immediate value, ra is register index, others are 0.
        """
        # Extract register index directly
        cdef uint8_t ra = clamp_12(<uint8_t>(program.zeta[program_counter + 1] % 16))
        
        # Extract 64-bit immediate using pointer arithmetic (8 bytes)
        cdef uint64_t vx = 0
        cdef uint32_t i
        for i in range(8):
            vx |= (<uint64_t>program.zeta[program_counter + 2 + i]) << (8 * i)
        
        # Return InstructionProps struct
        cdef InstructionProps props
        props.vx = vx
        props.vy = 0  # Not used in this instruction type
        props.ra = ra
        props.rb = 0  # Not used in this instruction type
        props.rd = 0  # Not used in this instruction type
        
        return props

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = load_imm_64_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[20] = _e

