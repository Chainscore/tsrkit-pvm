# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from ...cy_status cimport PVM_HOST, PvmExit
from ...cy_utils cimport chi, clamp_4
from ..cy_table cimport CyTable, CyTableEntry, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

cdef inline uint32_t ecalli_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """
    OPC10: Ecalli - Execute call immediate.
    Performs a host call with the immediate value.
    
    Args:
        program: Current program state
        registers: Current register state
        memory: Current memory state  
        counter: Current program counter
        vx: Immediate value to pass to host
        vy, ra, rb, rd: Unused for this instruction
        
    Returns:
        Tuple of (execution_status, next_pc)
    """
    raise PvmExit(PVM_HOST, vx)

cdef class CyInstructionsWArgs1Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 immediate argument.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract immediate value from program bytes.
        Returns InstructionProps struct where vx is the immediate value, others are 0.
        """
        cdef uint32_t lx = clamp_4(<uint8_t>skip_index)
        cdef uint32_t start = program_counter + 1
        
        # Extract immediate value using pointer arithmetic
        cdef uint64_t immediate_value = 0
        cdef uint32_t i
        for i in range(lx):
            immediate_value |= (<uint64_t>program.zeta[start + i]) << (8 * i)
        
        # Apply chi transformation
        cdef uint64_t vx = <uint64_t>chi(<uint64_t>immediate_value, <uint8_t>lx)
        
        # Return InstructionProps struct
        cdef InstructionProps props
        props.vx = vx
        props.vy = 0  # Not used in single immediate instructions
        props.ra = 0  # Not used in immediate instructions
        props.rb = 0  # Not used in immediate instructions
        props.rd = 0  # Not used in immediate instructions
        
        return props

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = ecalli_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[10] = _e

