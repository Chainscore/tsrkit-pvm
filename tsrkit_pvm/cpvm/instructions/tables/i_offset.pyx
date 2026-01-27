# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from ...cy_status cimport PVM_CONTINUE, CONTINUE, CyStatus
from ...cy_utils cimport clamp_4, z
from ..cy_table cimport CyTable, CyTableEntry, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

# Unified dispatch function for jump instruction
cdef inline uint32_t jump_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """
    OPC40: Unconditional jump to specified offset.
    
    Args:
        program: Current program state
        registers: Register array 
        memory: Memory object
        counter: Current program counter
        vx: Target jump address
        vy, ra, rb, rd: Unused for this instruction
    """
    return program.branch(counter, vx, True)

cdef class CyWArgsOneOffset(CyTable):
    """
    Cython optimized instruction table for instructions with 1 offset argument.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract offset value from program bytes.
        Returns InstructionProps struct where vx is the computed offset, others are 0.
        """
        cdef uint32_t lx = clamp_4(<uint8_t>skip_index)
        cdef uint32_t start = program_counter + 1
        
        # Extract offset using pointer arithmetic
        cdef uint32_t raw_offset = 0
        cdef uint32_t i
        for i in range(lx):
            raw_offset |= (<uint32_t>program.zeta[start + i]) << (8 * i)
        
        cdef uint64_t vx = <uint64_t>(program_counter) + <uint64_t>z(<uint64_t>raw_offset, <uint8_t>lx)
        
        # Return InstructionProps struct
        cdef InstructionProps props
        props.vx = vx
        props.vy = 0  # Not used in offset instructions
        props.ra = 0  # Not used in offset instructions
        props.rb = 0  # Not used in offset instructions
        props.rd = 0  # Not used in offset instructions
        
        return props

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = jump_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[40] = _e

