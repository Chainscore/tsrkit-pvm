# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, uint64_t, uint8_t
from ...cy_utils cimport chi, clamp_12, clamp_4
from ..cy_table cimport CyTable, CyTableEntry, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram


cdef inline uint32_t jump_ind_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC50: Indirect jump to address in register + offset."""
    cdef uint32_t addr_calc = registers[ra] + vx
    return program.djump(counter, addr_calc)

cdef inline uint32_t load_imm_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC51: Load immediate value into register."""
    registers[ra] = vx
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t load_u8_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC52: Load unsigned 8-bit value from memory."""
    cdef bytes data = memory.read(vx, 1)
    registers[ra] = int.from_bytes(data, "little")
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t load_i8_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC53: Load signed 8-bit value from memory."""
    cdef bytes data = memory.read(vx, 1)
    registers[ra] = <uint64_t>chi(<uint64_t>int.from_bytes(data, "little"), <uint8_t>1)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t load_u16_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC54: Load unsigned 16-bit value from memory."""
    cdef bytes data = memory.read(vx, 2)
    registers[ra] = int.from_bytes(data, "little")
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t load_i16_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC55: Load signed 16-bit value from memory."""
    cdef bytes data = memory.read(vx, 2)
    registers[ra] = <uint64_t>chi(<uint64_t>int.from_bytes(data, "little"), <uint8_t>2)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t load_u32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC56: Load unsigned 32-bit value from memory."""
    cdef bytes data = memory.read(vx, 4)
    registers[ra] = int.from_bytes(data, "little")
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t load_i32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC57: Load signed 32-bit value from memory."""
    cdef bytes data = memory.read(vx, 4)
    registers[ra] = <uint64_t>chi(<uint64_t>int.from_bytes(data, "little"), <uint8_t>4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t load_u64_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC58: Load unsigned 64-bit value from memory."""
    cdef bytes data = memory.read(vx, 8)
    registers[ra] = int.from_bytes(data, "little")
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t store_u8_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC59: Store 8-bit value to memory."""
    memory.write(vx, int(registers[ra] % (2**8)).to_bytes(1, "little"))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t store_u16_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC60: Store 16-bit value to memory."""
    memory.write(vx, int(registers[ra] % (2**16)).to_bytes(2, "little"))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t store_u32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC61: Store 32-bit value to memory."""
    memory.write(vx, int(registers[ra] % (2**32)).to_bytes(4, "little"))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t store_u64_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC62: Store 64-bit value to memory."""
    memory.write(vx, registers[ra].to_bytes(8, "little"))
    return <uint32_t>0xFFFFFFFF

cdef class CyInstructionsWArgs1Reg1Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 1 register + 1 immediate argument.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract register and immediate arguments from program bytes.
        Returns InstructionProps struct where vx is the immediate value, ra is register index, others are 0.
        """
        cdef uint32_t lx = clamp_4(<uint8_t>max(0, skip_index - 1))
        
        # Extract register index directly
        cdef uint8_t ra = clamp_12(<uint8_t>(program.zeta[program_counter + 1] % 16))
        
        # Extract immediate value using pointer arithmetic
        cdef uint64_t vx = 0
        cdef uint32_t i
        for i in range(min(lx, 8)):  # Ensure we don't read more than 8 bytes
            vx |= (<uint64_t>program.zeta[program_counter + 2 + i]) << (8 * i)
        vx = <uint64_t>chi(<uint64_t>vx, <uint8_t>lx)
        
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