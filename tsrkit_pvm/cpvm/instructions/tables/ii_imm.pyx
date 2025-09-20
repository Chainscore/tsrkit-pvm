# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, uint64_t, uint8_t, uint16_t, int8_t
from ...cy_status cimport CONTINUE
from ...cy_utils cimport chi, clamp_4, clamp_4_max0
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram


cdef inline uint32_t store_imm_u8_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC30: Store immediate 8-bit value."""
    cdef uint8_t value = <uint8_t>(vy % 2**8)
    cdef uint64_t address = <uint64_t>vx
    memory.write(address & 0xFFFFFFFF, value.to_bytes(1, 'little'))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t store_imm_u16_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC31: Store immediate 16-bit value."""
    cdef uint16_t value = <uint16_t>(vy % 2**16)
    cdef uint64_t address = <uint64_t>vx
    memory.write(address & 0xFFFFFFFF, value.to_bytes(2, 'little'))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t store_imm_u32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC32: Store immediate 32-bit value."""
    cdef uint32_t value = <uint32_t>(vy % 2**32)
    cdef uint64_t address = <uint64_t>vx
    memory.write(address & 0xFFFFFFFF, value.to_bytes(4, 'little'))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t store_imm_u64_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC33: Store immediate 64-bit value."""
    cdef uint64_t value = <uint64_t>(vy % 2**64)
    cdef uint64_t address = <uint64_t>vx
    memory.write(address & 0xFFFFFFFF, value.to_bytes(8, 'little'))
    return <uint32_t>0xFFFFFFFF

cdef class CyInstructionsWArgs2Imm(CyTable):
    """
    Cython optimized instruction table for 2 immediate argument instructions.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract two immediate arguments from the instruction stream.
        Returns InstructionProps struct where vx/vy are the immediate values, others are 0.
        """
        cdef uint32_t lx = clamp_4(<uint8_t>program.zeta[program_counter + 1])
        cdef uint32_t ly = clamp_4_max0(<int8_t>(skip_index - int(lx) - 1))
        
        # Extract first immediate (vx) using pointer arithmetic
        cdef uint32_t start = program_counter + 2
        cdef uint64_t vx = 0
        cdef uint32_t i
        for i in range(lx):
            vx |= (<uint64_t>program.zeta[start + i]) << (8 * i)
        vx = <uint64_t>chi(<uint64_t>vx, <uint8_t>lx)
        
        # Extract second immediate (vy) using pointer arithmetic
        start = program_counter + 2 + lx
        cdef uint64_t vy = 0
        for i in range(ly):
            vy |= (<uint64_t>program.zeta[start + i]) << (8 * i)
        vy = <uint64_t>chi(<uint64_t>vy, <uint8_t>ly)

        # Return InstructionProps struct
        cdef InstructionProps props
        props.vx = vx
        props.vy = vy
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
_e = CyTableEntry(); _e.fn = store_imm_u8_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[30] = _e
_e = CyTableEntry(); _e.fn = store_imm_u16_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[31] = _e
_e = CyTableEntry(); _e.fn = store_imm_u32_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[32] = _e
_e = CyTableEntry(); _e.fn = store_imm_u64_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[33] = _e
