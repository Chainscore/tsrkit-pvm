# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, uint64_t, uint8_t, int8_t

from ...cy_status cimport CONTINUE
from ...cy_utils cimport chi, clamp_12, clamp_4, clamp_4_max0
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram


# Store immediate indirect instructions
cdef inline tuple store_imm_ind_u8_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC70: Store immediate vy as u8 at address (ra + vx)."""
    value = int(vy % (2**8))
    memory.write((registers[ra] + vx) & 0xFFFFFFFF, value.to_bytes(1, "little"))
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef inline tuple store_imm_ind_u16_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC71: Store immediate vy as u16 at address (ra + vx)."""
    value = int(vy % (2**16))
    memory.write((registers[ra] + vx) & 0xFFFFFFFF, value.to_bytes(2, "little"))
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef inline tuple store_imm_ind_u32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC72: Store immediate vy as u32 at address (ra + vx)."""
    value = int(vy % (2**32))
    memory.write((registers[ra] + vx) & 0xFFFFFFFF, value.to_bytes(4, "little"))
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef inline tuple store_imm_ind_u64_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC73: Store immediate vy as u64 at address (ra + vx)."""
    value = int(vy % (2**64))
    memory.write((registers[ra] + vx) & 0xFFFFFFFF, value.to_bytes(8, "little"))
    return CONTINUE, <uint32_t>0xFFFFFFFF

cdef class CyInstructionsWArgs1Reg2Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 register + 2 immediate arguments.
    """
    
    cpdef tuple get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract register and two immediate arguments from program bytes.
        Returns (vx, vy, ra, rb, rd) where vx/vy are immediate values, ra is register, others are 0.
        """
        cdef uint32_t byte_val = program.zeta[program_counter + 1]
        cdef uint8_t ra = clamp_12(<uint8_t>(byte_val & 0x0F))           # Lower 4 bits
        cdef uint32_t lx = clamp_4(<uint8_t>((byte_val >> 4) & 0x07))     # Next 3 bits
        cdef uint32_t ly = clamp_4_max0(<int8_t>(skip_index - lx - 1))
        
        # Extract first immediate value
        cdef uint32_t start = program_counter + 2
        cdef uint32_t end = start + lx
        cdef bytes vx_slice = program.zeta[start:end]
        cdef uint64_t vx = 0
        if lx > 0:
            vx = <uint64_t>chi(<uint64_t>int.from_bytes(vx_slice, "little"), <uint8_t>lx)
        
        # Extract second immediate value
        start = program_counter + 2 + lx
        end = start + ly
        cdef bytes vy_slice = program.zeta[start:end]
        cdef uint64_t vy = 0
        if ly > 0:
            vy = <uint64_t>chi(<uint64_t>int.from_bytes(vy_slice, "little"), <uint8_t>ly)
        
        # Return in unified format: (vx, vy, ra, rb, rd)
        return (vx, vy, ra, 0, 0)

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
