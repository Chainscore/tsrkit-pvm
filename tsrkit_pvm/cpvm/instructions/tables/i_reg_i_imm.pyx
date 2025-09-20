# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

"""
Cython optimized i_reg_i_imm instruction table.
Instructions with 1 register + 1 immediate argument (opcodes 50-62).
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from ...cy_status cimport CONTINUE
from ...cy_utils cimport chi, clamp_12, clamp_4
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

# Unified dispatch functions

cdef tuple jump_ind_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC50: Indirect jump to address in register + offset."""
    from math import floor
    status, counter = program.djump(counter, floor(int(registers[ra]) + vx) % 2**32)
    return (status, counter)

cdef tuple load_imm_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC51: Load immediate value into register."""
    registers[ra] = vx
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple load_u8_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC52: Load unsigned 8-bit value from memory."""
    cdef bytes data = memory.read(vx & 0xFFFFFFFF, 1)
    registers[ra] = int.from_bytes(data, "little")
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple load_i8_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC53: Load signed 8-bit value from memory."""
    cdef bytes data = memory.read(vx & 0xFFFFFFFF, 1)
    registers[ra] = <uint64_t>chi(<uint64_t>int.from_bytes(data, "little"), <uint8_t>1)
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple load_u16_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC54: Load unsigned 16-bit value from memory."""
    cdef bytes data = memory.read(vx & 0xFFFFFFFF, 2)
    registers[ra] = int.from_bytes(data, "little")
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple load_i16_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC55: Load signed 16-bit value from memory."""
    cdef bytes data = memory.read(vx & 0xFFFFFFFF, 2)
    registers[ra] = <uint64_t>chi(<uint64_t>int.from_bytes(data, "little"), <uint8_t>2)
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple load_u32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC56: Load unsigned 32-bit value from memory."""
    cdef bytes data = memory.read(vx & 0xFFFFFFFF, 4)
    registers[ra] = int.from_bytes(data, "little")
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple load_i32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC57: Load signed 32-bit value from memory."""
    cdef bytes data = memory.read(vx & 0xFFFFFFFF, 4)
    registers[ra] = <uint64_t>chi(<uint64_t>int.from_bytes(data, "little"), <uint8_t>4)
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple load_u64_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC58: Load unsigned 64-bit value from memory."""
    cdef bytes data = memory.read(vx & 0xFFFFFFFF, 8)
    registers[ra] = int.from_bytes(data, "little")
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple store_u8_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC59: Store 8-bit value to memory."""
    memory.write(vx & 0xFFFFFFFF, int(registers[ra] % (2**8)).to_bytes(1, "little"))
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple store_u16_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC60: Store 16-bit value to memory."""
    memory.write(vx & 0xFFFFFFFF, int(registers[ra] % (2**16)).to_bytes(2, "little"))
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple store_u32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC61: Store 32-bit value to memory."""
    memory.write(vx & 0xFFFFFFFF, int(registers[ra] % (2**32)).to_bytes(4, "little"))
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef tuple store_u64_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC62: Store 64-bit value to memory."""
    memory.write(vx & 0xFFFFFFFF, registers[ra].to_bytes(8, "little"))
    return (CONTINUE, <uint32_t>0xFFFFFFFF)

cdef class CyInstructionsWArgs1Reg1Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 register + 1 immediate argument.
    """
    
    cpdef tuple get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract register and immediate arguments from program bytes.
        Returns (vx, vy, ra, rb, rd) where vx is the immediate value, ra is register index, others are 0.
        """
        cdef uint32_t lx = clamp_4(<uint8_t>max(0, skip_index - 1))
        
        # Extract bytes: 1 for register + lx for immediate
        cdef bytes zeta_slice = program.zeta[program_counter + 1: program_counter + 1 + 1 + lx]
        cdef uint8_t ra = clamp_12(<uint8_t>(zeta_slice[0] % 16))  # FIXED: Missing % 16
        cdef bytes vx_bytes = bytes(zeta_slice[1:9])
        cdef uint64_t vx = <uint64_t>chi(<uint64_t>int.from_bytes(vx_bytes, "little"), <uint8_t>lx)
        
        # Return in unified format: (vx, vy, ra, rb, rd)
        return (vx, 0, ra, 0, 0)
    
    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = jump_ind_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[50] = _e
_e = CyTableEntry(); _e.fn = load_imm_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[51] = _e
_e = CyTableEntry(); _e.fn = load_u8_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[52] = _e
_e = CyTableEntry(); _e.fn = load_i8_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[53] = _e
_e = CyTableEntry(); _e.fn = load_u16_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[54] = _e
_e = CyTableEntry(); _e.fn = load_i16_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[55] = _e
_e = CyTableEntry(); _e.fn = load_u32_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[56] = _e
_e = CyTableEntry(); _e.fn = load_i32_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[57] = _e
_e = CyTableEntry(); _e.fn = load_u64_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[58] = _e
_e = CyTableEntry(); _e.fn = store_u8_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[59] = _e
_e = CyTableEntry(); _e.fn = store_u16_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[60] = _e
_e = CyTableEntry(); _e.fn = store_u32_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[61] = _e
_e = CyTableEntry(); _e.fn = store_u64_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[62] = _e