# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, int64_t, uint64_t, uint8_t, uint16_t, int32_t, int8_t, int16_t
from ...cy_utils cimport b, b_inv, chi, z, z_inv, clamp_12, clamp_4, clamp_4_max0
from ...cy_utils cimport uint64_to_bytes_le, uint32_to_bytes_le, uint16_to_bytes_le, uint8_to_bytes_le
from ...cy_utils cimport bytes_to_uint64_le, bytes_to_uint32_le, bytes_to_uint16_le, bytes_to_uint8_le
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram


# Store indirect instructions
cdef inline uint32_t  store_ind_u8(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC120: Store register ra as u8 to address (rb + vx)."""
    memory.write(registers[rb] + vx, uint8_to_bytes_le(<uint8_t>(registers[ra] & 0xFF), 1))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  store_ind_u16(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC121: Store register ra as u16 to address (rb + vx)."""
    memory.write(registers[rb] + vx, uint16_to_bytes_le(<uint16_t>(registers[ra] & 0xFFFF), 2))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  store_ind_u32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC122: Store register ra as u32 to address (rb + vx)."""
    memory.write(registers[rb] + vx, uint32_to_bytes_le(<uint32_t>(registers[ra] & 0xFFFFFFFF), 4))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  store_ind_u64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC123: Store register ra as u64 to address (rb + vx)."""
    memory.write(registers[rb] + vx, uint64_to_bytes_le(registers[ra], 8))
    return <uint32_t>0xFFFFFFFF

# Load indirect instructions
cdef inline uint32_t  load_ind_u8(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC124: Load u8 from address (rb + vx) to register ra."""
    cdef bytes data = memory.read(registers[rb] + vx, 1)
    registers[ra] = bytes_to_uint8_le(data)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  load_ind_i8(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC125: Load i8 from address (rb + vx) to register ra."""
    cdef bytes data = memory.read(registers[rb] + vx, 1)
    cdef uint8_t value = bytes_to_uint8_le(data)
    # Sign extend from 8-bit to 64-bit
    registers[ra] = <uint64_t>(<int8_t>value)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  load_ind_u16(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC126: Load u16 from address (rb + vx) to register ra."""
    cdef bytes data = memory.read(registers[rb] + vx, 2)
    registers[ra] = bytes_to_uint16_le(data)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  load_ind_i16(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC127: Load i16 from address (rb + vx) to register ra."""
    cdef bytes data = memory.read(registers[rb] + vx, 2)
    cdef uint16_t value = bytes_to_uint16_le(data)
    # Sign extend from 16-bit to 64-bit
    registers[ra] = <uint64_t>(<int16_t>value)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  load_ind_u32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC128: Load u32 from address (rb + vx) to register ra."""
    cdef bytes data = memory.read(registers[rb] + vx, 4)
    registers[ra] = bytes_to_uint32_le(data)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  load_ind_i32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC129: Load i32 from address (rb + vx) to register ra."""
    cdef bytes data = memory.read(registers[rb] + vx, 4)
    cdef uint32_t value = bytes_to_uint32_le(data)
    registers[ra] = <uint64_t>(<int32_t>value)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  load_ind_u64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC130: Load u64 from address (rb + vx) to register ra."""
    cdef bytes data = memory.read(registers[rb] + vx, 8)
    registers[ra] = bytes_to_uint64_le(data)
    return <uint32_t>0xFFFFFFFF

# Arithmetic and logic operations with immediate values
cdef inline uint32_t  add_imm_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC131: Add immediate value to register (32-bit)."""
    cdef uint32_t value = <uint32_t>(registers[rb] + vx)
    registers[ra] = chi(value, 4)
    return <uint32_t>0xFFFFFFFF
# Bitwise operations
cdef inline uint32_t  and_op(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC210: Bitwise AND."""
    registers[rd] = registers[ra] & registers[rb]
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  xor_op(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC211: Bitwise XOR."""
    registers[rd] = registers[ra] ^ registers[rb]
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  or_op(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC212: Bitwise OR."""
    registers[rd] = registers[ra] | registers[rb]
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  mul_imm_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC135: Multiply with immediate value (32-bit)."""
    cdef uint32_t value = <uint32_t>(registers[rb] * vx)
    registers[ra] = chi(value, 4)
    return <uint32_t>0xFFFFFFFF

# Bitwise operations with immediate values
cdef inline uint32_t  and_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC132: Bitwise AND with immediate."""
    registers[ra] = registers[rb] & vx
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  xor_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC133: Bitwise XOR with immediate."""
    registers[ra] = registers[rb] ^ vx
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  or_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC134: Bitwise OR with immediate."""
    registers[ra] = registers[rb] | vx
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  set_lt_u_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC136: Set if less than (unsigned) immediate."""
    registers[ra] = 1 if registers[rb] < vx else 0
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  set_lt_s_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC137: Set if less than (signed) immediate."""
    cdef int64_t a = <int64_t>(registers[rb])
    cdef int64_t b = <int64_t>(vx)
    registers[ra] = 1 if a < b else 0
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_l_imm_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC138: Shift left immediate (32-bit)."""
    cdef uint32_t value = <uint32_t>(registers[rb] & 0xFFFFFFFF)
    cdef uint32_t shift = <uint32_t>(vx % 32)
    cdef uint32_t result = value << shift
    registers[ra] = chi(result, 4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_r_imm_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC139: Shift right logical immediate (32-bit)."""
    cdef uint32_t value = <uint32_t>(registers[rb])
    cdef uint32_t shift = <uint32_t>(vx % 32)
    cdef uint32_t result = value >> shift
    registers[ra] = chi(result, 4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shar_r_imm_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC140: Shift right arithmetic immediate (32-bit)."""
    cdef int64_t signed_value = z(registers[rb], 4)
    cdef uint32_t shift = <uint32_t>(vx % 32)
    cdef int64_t result = signed_value >> shift
    registers[ra] = z_inv(result, 8)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  neg_add_imm_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC141: Negate and add immediate (32-bit)."""
    cdef uint32_t result = <uint32_t>((vx - registers[rb]))
    registers[ra] = chi(result, 4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  set_gt_u_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC142: Set if greater than (unsigned) immediate."""
    registers[ra] = 1 if registers[rb] > vx else 0
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  set_gt_s_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC143: Set if greater than (signed) immediate."""
    cdef int64_t a = z(registers[rb], 8)
    cdef int64_t b = z(vx, 8)
    registers[ra] = 1 if a > b else 0
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_l_imm_alt_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC144: Shift left immediate alternate (32-bit) - operands swapped."""
    cdef uint32_t value = <uint32_t>(vx)
    cdef uint32_t shift = <uint32_t>(registers[rb] % 32)
    cdef uint32_t result = value << shift
    registers[ra] = chi(result, 4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_r_imm_alt_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC145: Shift right logical immediate alternate (32-bit) - operands swapped."""
    cdef uint32_t value = <uint32_t>(vx)
    cdef uint32_t shift = <uint32_t>(registers[rb] % 32)
    cdef uint32_t result = value >> shift
    registers[ra] = chi(result, 4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shar_r_imm_alt_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC146: Shift right arithmetic immediate alternate (32-bit) - operands swapped."""
    cdef int64_t signed_value = z(vx, 4)
    cdef uint32_t shift = <uint32_t>(registers[rb] % 32)
    cdef int64_t result = signed_value >> shift
    registers[ra] = z_inv(result, 8)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  cmov_iz_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC147: Conditional move if zero immediate."""
    if registers[rb] == 0:
        registers[ra] = vx
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  cmov_nz_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC148: Conditional move if not zero immediate."""
    if registers[rb] != 0:
        registers[ra] = vx
    return <uint32_t>0xFFFFFFFF

# 64-bit operations
cdef inline uint32_t  add_imm_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC149: Add immediate value to register (64-bit)."""
    registers[ra] = registers[rb] + vx
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  mul_imm_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC150: Multiply with immediate value (64-bit)."""
    registers[ra] = registers[rb] * vx
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_l_imm_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC151: Shift left immediate (64-bit)."""
    cdef uint64_t value = registers[rb]
    cdef uint64_t shift = vx % 64
    registers[ra] = chi(value << shift, 8)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_r_imm_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC152: Shift right logical immediate (64-bit)."""
    cdef uint64_t value = registers[rb]
    cdef uint64_t shift = vx % 64
    registers[ra] = chi(value >> shift, 8)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shar_r_imm_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC153: Shift right arithmetic immediate (64-bit)."""
    cdef int64_t signed_value = z(registers[rb], 8)
    cdef uint64_t shift = vx % 64
    cdef int64_t result = signed_value >> shift
    registers[ra] = z_inv(result, 8)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_l_imm_alt_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC155: Shift left immediate alternate (64-bit) - operands swapped."""
    cdef uint64_t value = vx
    cdef uint64_t shift = registers[rb] % 64
    registers[ra] = chi(value << shift, 8)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_r_imm_alt_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC156: Shift right logical immediate alternate (64-bit) - operands swapped."""
    cdef uint64_t value = vx
    cdef uint64_t shift = registers[rb] % 64
    registers[ra] = chi(value >> shift, 8)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shar_r_imm_alt_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC157: Shift right arithmetic immediate alternate (64-bit) - operands swapped."""
    cdef int64_t signed_value = z(vx, 8)
    cdef uint64_t shift = registers[rb] % 64
    cdef int64_t result = signed_value >> shift
    registers[ra] = z_inv(result, 8)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  neg_add_imm_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC154: Negate and add immediate (64-bit)."""
    registers[ra] = vx - registers[rb]
    return <uint32_t>0xFFFFFFFF

# Rotation operations
cdef inline uint32_t  rot_r_64_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC158: Rotate right 64-bit immediate."""
    cdef uint64_t value = registers[rb]
    cdef uint64_t shift = vx % 64
    registers[ra] = (value >> shift) | (value << (64 - shift))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  rot_r_64_imm_alt(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC159: Rotate right 64-bit immediate alternate - operands swapped."""
    cdef uint64_t value = vx
    cdef uint64_t shift = registers[rb] % 64
    registers[ra] = (value >> shift) | (value << (64 - shift))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  rot_r_32_imm(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC160: Rotate right 32-bit immediate."""
    cdef uint32_t value = <uint32_t>(registers[rb])
    cdef uint32_t shift = <uint32_t>(vx % 32)
    cdef uint32_t result = (value >> shift) | (value << (32 - shift))
    registers[ra] = chi(result, 4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  rot_r_32_imm_alt(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC161: Rotate right 32-bit immediate alternate - operands swapped."""
    cdef uint32_t value = <uint32_t>(vx)
    cdef uint32_t shift = <uint32_t>(registers[rb] % 32)
    cdef uint32_t result = (value >> shift) | (value << (32 - shift))
    registers[ra] = chi(result, 4)
    return <uint32_t>0xFFFFFFFF


cdef class CyInstructionsWArgs2Reg1Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 2 register + 1 immediate argument.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract two registers and immediate arguments from program bytes.
        Returns InstructionProps struct where vx is immediate, ra/rb are registers, others are 0.
        """
        cdef uint8_t* zeta_ptr = program.zeta
        cdef uint32_t byte_val = zeta_ptr[program_counter + 1]
        cdef uint8_t ra = clamp_12(byte_val & 0x0F)  # Lower 4 bits
        cdef uint8_t rb = clamp_12(byte_val >> 4)    # Upper 4 bits
        cdef uint32_t lx = clamp_4_max0(skip_index - 1)
        
        cdef uint64_t vx = 0
        cdef uint32_t i
        cdef uint32_t start = program_counter + 2
        
        # Extract immediate value using pointer arithmetic
        if lx > 0:
            for i in range(lx):
                vx |= (<uint64_t>zeta_ptr[start + i]) << (8 * i)
            vx = <uint64_t>chi(<uint64_t>vx, <uint8_t>lx)
        
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

# Store instructions (120-123)
_e = CyTableEntry(); _e.fn = store_ind_u8; _e.gas_cost = 1; _e.is_terminating = False; TABLE[120] = _e
_e = CyTableEntry(); _e.fn = store_ind_u16; _e.gas_cost = 1; _e.is_terminating = False; TABLE[121] = _e
_e = CyTableEntry(); _e.fn = store_ind_u32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[122] = _e
_e = CyTableEntry(); _e.fn = store_ind_u64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[123] = _e

# Load instructions (124-130) 
_e = CyTableEntry(); _e.fn = load_ind_u8; _e.gas_cost = 1; _e.is_terminating = False; TABLE[124] = _e
_e = CyTableEntry(); _e.fn = load_ind_i8; _e.gas_cost = 1; _e.is_terminating = False; TABLE[125] = _e
_e = CyTableEntry(); _e.fn = load_ind_u16; _e.gas_cost = 1; _e.is_terminating = False; TABLE[126] = _e
_e = CyTableEntry(); _e.fn = load_ind_i16; _e.gas_cost = 1; _e.is_terminating = False; TABLE[127] = _e
_e = CyTableEntry(); _e.fn = load_ind_u32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[128] = _e
_e = CyTableEntry(); _e.fn = load_ind_i32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[129] = _e
_e = CyTableEntry(); _e.fn = load_ind_u64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[130] = _e

# Arithmetic and logic instructions (131-159)
_e = CyTableEntry(); _e.fn = add_imm_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[131] = _e
_e = CyTableEntry(); _e.fn = and_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[132] = _e
_e = CyTableEntry(); _e.fn = xor_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[133] = _e
_e = CyTableEntry(); _e.fn = or_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[134] = _e
_e = CyTableEntry(); _e.fn = mul_imm_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[135] = _e
_e = CyTableEntry(); _e.fn = set_lt_u_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[136] = _e
_e = CyTableEntry(); _e.fn = set_lt_s_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[137] = _e
_e = CyTableEntry(); _e.fn = shlo_l_imm_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[138] = _e
_e = CyTableEntry(); _e.fn = shlo_r_imm_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[139] = _e
_e = CyTableEntry(); _e.fn = shar_r_imm_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[140] = _e
_e = CyTableEntry(); _e.fn = neg_add_imm_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[141] = _e
_e = CyTableEntry(); _e.fn = set_gt_u_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[142] = _e
_e = CyTableEntry(); _e.fn = set_gt_s_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[143] = _e
_e = CyTableEntry(); _e.fn = shlo_l_imm_alt_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[144] = _e
_e = CyTableEntry(); _e.fn = shlo_r_imm_alt_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[145] = _e
_e = CyTableEntry(); _e.fn = shar_r_imm_alt_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[146] = _e
_e = CyTableEntry(); _e.fn = cmov_iz_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[147] = _e
_e = CyTableEntry(); _e.fn = cmov_nz_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[148] = _e

# 64-bit operations (149-161)
_e = CyTableEntry(); _e.fn = add_imm_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[149] = _e
_e = CyTableEntry(); _e.fn = mul_imm_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[150] = _e
_e = CyTableEntry(); _e.fn = shlo_l_imm_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[151] = _e
_e = CyTableEntry(); _e.fn = shlo_r_imm_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[152] = _e
_e = CyTableEntry(); _e.fn = shar_r_imm_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[153] = _e
_e = CyTableEntry(); _e.fn = neg_add_imm_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[154] = _e
_e = CyTableEntry(); _e.fn = shlo_l_imm_alt_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[155] = _e
_e = CyTableEntry(); _e.fn = shlo_r_imm_alt_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[156] = _e
_e = CyTableEntry(); _e.fn = shar_r_imm_alt_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[157] = _e
_e = CyTableEntry(); _e.fn = rot_r_64_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[158] = _e
_e = CyTableEntry(); _e.fn = rot_r_64_imm_alt; _e.gas_cost = 1; _e.is_terminating = False; TABLE[159] = _e
_e = CyTableEntry(); _e.fn = rot_r_32_imm; _e.gas_cost = 1; _e.is_terminating = False; TABLE[160] = _e
_e = CyTableEntry(); _e.fn = rot_r_32_imm_alt; _e.gas_cost = 1; _e.is_terminating = False; TABLE[161] = _e
