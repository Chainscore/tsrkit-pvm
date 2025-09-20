# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, int64_t, uint64_t, uint8_t, int8_t
from ...cy_utils cimport clamp_12, clamp_4_max0, z
from ..cy_table cimport CyTable, CyTableEntry, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram


cdef inline uint32_t branch_eq_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC170: Branch if ra == rb to offset vx."""
    return program.branch(counter, vx, registers[ra] == registers[rb])

cdef inline uint32_t branch_ne_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC171: Branch if ra != rb to offset vx."""
    return program.branch(counter, vx, registers[ra] != registers[rb])

cdef inline uint32_t branch_lt_u_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC172: Branch if ra < rb (unsigned) to offset vx."""
    return program.branch(counter, vx, registers[ra] < registers[rb])

cdef inline uint32_t branch_lt_s_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC173: Branch if ra < rb (signed) to offset vx."""
    return program.branch(counter, vx, <int64_t>registers[ra] < <int64_t>registers[rb])

cdef inline uint32_t branch_ge_u_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC174: Branch if ra >= rb (unsigned) to offset vx."""
    return program.branch(counter, vx, registers[ra] >= registers[rb])

cdef inline uint32_t branch_ge_s_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC175: Branch if ra >= rb (signed) to offset vx."""
    return program.branch(counter, vx, <int64_t>registers[ra] >= <int64_t>registers[rb])

cdef class CyInstructionsWArgs2Reg1Offset(CyTable):
    """
    Cython optimized instruction table for instructions with 2 register + 1 offset argument.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract register indices and offset value from program bytes.
        Returns InstructionProps struct where vx is offset, ra/rb are registers, others are 0.
        """
        cdef uint8_t* zeta_ptr = program.zeta
        cdef uint32_t byte_val = zeta_ptr[program_counter + 1]
        
        cdef uint8_t ra = clamp_12(<uint8_t>(byte_val & 0x0F))  # Lower 4 bits
        cdef uint8_t rb = clamp_12(<uint8_t>(byte_val >> 4))    # Upper 4 bits
        cdef uint32_t lx = clamp_4_max0(<int8_t>(skip_index - 1))
        
        cdef uint64_t vx
        cdef uint32_t raw_offset = 0
        cdef uint32_t i
        cdef uint32_t start = program_counter + 2
        
        # Extract offset using pointer arithmetic
        if lx > 0:
            for i in range(lx):
                raw_offset |= (<uint32_t>zeta_ptr[start + i]) << (8 * i)
            vx = <uint64_t>(program_counter) + <uint64_t>z(<uint64_t>raw_offset, <uint8_t>lx)
        else:
            vx = <uint64_t>program_counter
        
        # Return InstructionProps struct
        cdef InstructionProps props
        props.vx = vx
        props.vy = 0  # Not used in this instruction type
        props.ra = ra
        props.rb = rb
        props.rd = 0  # Not used in this instruction type
        
        return props

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = branch_eq_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[170] = _e
_e = CyTableEntry(); _e.fn = branch_ne_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[171] = _e
_e = CyTableEntry(); _e.fn = branch_lt_u_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[172] = _e
_e = CyTableEntry(); _e.fn = branch_lt_s_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[173] = _e
_e = CyTableEntry(); _e.fn = branch_ge_u_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[174] = _e
_e = CyTableEntry(); _e.fn = branch_ge_s_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[175] = _e
