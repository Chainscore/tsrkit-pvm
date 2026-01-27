# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, uint64_t, uint8_t, int8_t

from ...cy_status cimport CONTINUE
from ...cy_utils cimport chi, clamp_12, clamp_4, clamp_4_max0
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram


# Store immediate indirect instructions
cdef inline uint32_t store_imm_ind_u8_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC70: Store immediate vy as u8 at address (ra + vx)."""
    value = int(vy % (2**8))
    memory.write((registers[ra] + vx), value.to_bytes(1, "little"))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t store_imm_ind_u16_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC71: Store immediate vy as u16 at address (ra + vx)."""
    value = int(vy % (2**16))
    memory.write((registers[ra] + vx), value.to_bytes(2, "little"))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t store_imm_ind_u32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC72: Store immediate vy as u32 at address (ra + vx)."""
    value = int(vy % (2**32))
    memory.write((registers[ra] + vx), value.to_bytes(4, "little"))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t store_imm_ind_u64_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC73: Store immediate vy as u64 at address (ra + vx)."""
    value = int(vy % (2**64))
    memory.write((registers[ra] + vx), value.to_bytes(8, "little"))
    return <uint32_t>0xFFFFFFFF

cdef class CyInstructionsWArgs1Reg2Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 register + 2 immediate arguments.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract register and two immediate arguments from program bytes.
        Returns InstructionProps struct where vx/vy are immediate values, ra is register, others are 0.
        """
        cdef uint8_t* zeta_ptr = program.zeta
        cdef uint32_t byte_val = zeta_ptr[program_counter + 1]
        cdef uint8_t ra = clamp_12(<uint8_t>(byte_val & 0x0F))           # Lower 4 bits
        cdef uint32_t lx = clamp_4(<uint8_t>((byte_val >> 4) & 0x07))     # Next 3 bits
        cdef uint32_t ly = clamp_4_max0(<int8_t>(skip_index - lx - 1))
        
        # Extract first immediate value using pointer arithmetic
        cdef uint32_t start_x = program_counter + 2
        cdef uint64_t vx = 0
        cdef uint32_t i
        if lx > 0:
            for i in range(lx):
                vx |= (<uint64_t>zeta_ptr[start_x + i]) << (8 * i)
            vx = <uint64_t>chi(<uint64_t>vx, <uint8_t>lx)
        
        # Extract second immediate value using pointer arithmetic
        cdef uint32_t start_y = start_x + lx
        cdef uint64_t vy = 0
        if ly > 0:
            for i in range(ly):
                vy |= (<uint64_t>zeta_ptr[start_y + i]) << (8 * i)
            vy = <uint64_t>chi(<uint64_t>vy, <uint8_t>ly)
        
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
_e = CyTableEntry(); _e.fn = store_imm_ind_u8_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[70] = _e
_e = CyTableEntry(); _e.fn = store_imm_ind_u16_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[71] = _e
_e = CyTableEntry(); _e.fn = store_imm_ind_u32_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[72] = _e
_e = CyTableEntry(); _e.fn = store_imm_ind_u64_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[73] = _e
