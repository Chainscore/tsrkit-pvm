# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, uint64_t, uint8_t, int8_t
from ...cy_utils cimport chi, z, clamp_12, clamp_4, clamp_4_max0
from ..cy_table cimport CyTable, CyTableEntry, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

cdef inline uint32_t load_imm_jump_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC80: Load immediate value into register and jump to offset."""
    registers[ra] = vx
    return program.branch(counter, vy, True)

cdef inline uint32_t branch_eq_imm_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC81: Branch if register equals immediate."""
    cdef bint condition = registers[ra] == vx
    return program.branch(counter, vy, condition)

cdef inline uint32_t branch_ne_imm_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC82: Branch if register not equals immediate."""
    cdef bint condition = registers[ra] != vx
    return program.branch(counter, vy, condition)

cdef inline uint32_t branch_lt_u_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC83: Branch if register less than immediate (unsigned)."""
    cdef bint condition = registers[ra] < vx
    return program.branch(counter, vy, condition)

cdef inline uint32_t branch_le_u_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC84: Branch if register less than or equal immediate (unsigned)."""
    cdef bint condition = registers[ra] <= vx
    return program.branch(counter, vy, condition)

cdef inline uint32_t branch_ge_u_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC85: Branch if register greater than or equal immediate (unsigned)."""
    cdef bint condition = registers[ra] >= vx
    return program.branch(counter, vy, condition)

cdef inline uint32_t branch_gt_u_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC86: Branch if register greater than immediate (unsigned)."""
    cdef bint condition = registers[ra] > vx
    return program.branch(counter, vy, condition)

cdef inline uint32_t branch_lt_s_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC87: Branch if register less than immediate (signed)."""
    cdef bint condition = z(<uint64_t>registers[ra], <uint8_t>8) < z(<uint64_t>vx, <uint8_t>8)
    return program.branch(counter, vy, condition)

cdef inline uint32_t branch_le_s_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC88: Branch if register less than or equal immediate (signed)."""
    cdef bint condition = z(<uint64_t>registers[ra], <uint8_t>8) <= z(<uint64_t>vx, <uint8_t>8)
    return program.branch(counter, vy, condition)

cdef inline uint32_t branch_ge_s_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC89: Branch if register greater than or equal immediate (signed)."""
    cdef bint condition = z(<uint64_t>registers[ra], <uint8_t>8) >= z(<uint64_t>vx, <uint8_t>8)
    return program.branch(counter, vy, condition)

cdef inline uint32_t branch_gt_s_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC90: Branch if register greater than immediate (signed)."""
    cdef bint condition = z(<uint64_t>registers[ra], <uint8_t>8) > z(<uint64_t>vx, <uint8_t>8)
    return program.branch(counter, vy, condition)


cdef class InstructionsWArgs1Reg1Imm1Offset(CyTable):
    """
    Cython optimized instruction table for instructions with 1 register + 1 immediate + 1 offset argument.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract register, immediate, and offset arguments from program bytes.
        Returns InstructionProps struct where vx is immediate, vy is offset, ra is register, others are 0.
        """
        cdef uint8_t* zeta_ptr = program.zeta
        cdef uint32_t byte_val = zeta_ptr[program_counter + 1]
        
        cdef uint8_t ra = clamp_12(<uint8_t>(byte_val & 0x0F))           # Lower 4 bits
        cdef uint32_t lx = clamp_4(<uint8_t>((byte_val >> 4) & 0x07))     # Next 3 bits
        cdef uint32_t ly = clamp_4_max0(<int8_t>(int(skip_index) - lx - 1))
        
        # Extract immediate value using pointer arithmetic
        cdef uint64_t vx = 0
        cdef uint32_t i
        cdef uint32_t start_x = program_counter + 2
        if lx > 0:
            for i in range(lx):
                vx |= (<uint64_t>zeta_ptr[start_x + i]) << (8 * i)
            vx = <uint64_t>chi(<uint64_t>vx, <uint8_t>lx)
        
        # Extract offset value using pointer arithmetic
        cdef uint64_t vy = <uint64_t>program_counter
        cdef uint32_t start_y = start_x + lx
        cdef uint64_t offset_raw = 0
        if ly > 0:
            for i in range(ly):
                offset_raw |= (<uint64_t>zeta_ptr[start_y + i]) << (8 * i)
            vy = <uint64_t>(program_counter) + <uint64_t>z(<uint64_t>offset_raw, <uint8_t>ly)
        
        # Return InstructionProps struct
        cdef InstructionProps props
        props.vx = vx
        props.vy = vy
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
_e = CyTableEntry(); _e.fn = load_imm_jump_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[80] = _e
_e = CyTableEntry(); _e.fn = branch_eq_imm_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[81] = _e
_e = CyTableEntry(); _e.fn = branch_ne_imm_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[82] = _e
_e = CyTableEntry(); _e.fn = branch_lt_u_imm; _e.gas_cost = 1; _e.is_terminating = True; TABLE[83] = _e
_e = CyTableEntry(); _e.fn = branch_le_u_imm; _e.gas_cost = 1; _e.is_terminating = True; TABLE[84] = _e
_e = CyTableEntry(); _e.fn = branch_ge_u_imm; _e.gas_cost = 1; _e.is_terminating = True; TABLE[85] = _e
_e = CyTableEntry(); _e.fn = branch_gt_u_imm; _e.gas_cost = 1; _e.is_terminating = True; TABLE[86] = _e
_e = CyTableEntry(); _e.fn = branch_lt_s_imm; _e.gas_cost = 1; _e.is_terminating = True; TABLE[87] = _e
_e = CyTableEntry(); _e.fn = branch_le_s_imm; _e.gas_cost = 1; _e.is_terminating = True; TABLE[88] = _e
_e = CyTableEntry(); _e.fn = branch_ge_s_imm; _e.gas_cost = 1; _e.is_terminating = True; TABLE[89] = _e
_e = CyTableEntry(); _e.fn = branch_gt_s_imm; _e.gas_cost = 1; _e.is_terminating = True; TABLE[90] = _e
