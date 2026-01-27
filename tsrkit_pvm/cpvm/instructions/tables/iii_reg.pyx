# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=False
# cython: linetrace=False
# cython: nonecheck=False
# cython: initializedcheck=False
# cython: overflowcheck=False
# cython: infer_types=True
# cython: optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, int32_t, int64_t, uint32_t, uint64_t, uint8_t
from math import trunc
from ...cy_status cimport CONTINUE
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram
from ...cy_utils cimport chi, b_inv, b, clamp_12, smod, z, z_inv


# 32-bit arithmetic operations with C-level optimizations
cdef inline uint32_t add_32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC190: 32-bit addition."""
    cdef uint32_t a = <uint32_t>(registers[ra])
    cdef uint32_t b = <uint32_t>(registers[rb])
    cdef uint32_t result = a + b
    registers[rd] = <uint64_t>chi(<uint64_t>result, <uint8_t>4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t sub_32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC191: 32-bit subtraction."""
    cdef uint32_t a = <uint32_t>(registers[ra])
    cdef uint32_t b = <uint32_t>(registers[rb])
    cdef uint32_t result = a - b
    registers[rd] = <uint64_t>chi(<uint64_t>result, <uint8_t>4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t mul_32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC192: 32-bit multiplication."""
    cdef uint32_t a = <uint32_t>(registers[ra])
    cdef uint32_t b = <uint32_t>(registers[rb])
    cdef uint32_t result = a * b
    registers[rd] = <uint64_t>chi(<uint64_t>result, <uint8_t>4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t div_u_32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC193: 32-bit unsigned division."""
    cdef uint32_t a = <uint32_t>(registers[ra])
    cdef uint32_t b = <uint32_t>(registers[rb])
    if b == 0:
        registers[rd] = 0xFFFFFFFFFFFFFFFF  # 2**64 - 1
    else:
        registers[rd] = <uint64_t>chi(<uint64_t>(a // b), <uint8_t>4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t div_s_32_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC194: 32-bit signed division."""
    a = <int32_t>registers[ra]
    b = <int32_t>registers[rb]
    if b == 0:
        value = 2**64 - 1
    elif a == -(2**31) and b == -1:
        value = z_inv(a, 8)
    else:
        value = z_inv(trunc(a / b), 8)

    registers[rd] = value
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  rem_u_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC195: 32-bit unsigned remainder."""
    cdef uint32_t a = <uint32_t>(registers[ra])
    cdef uint32_t b = <uint32_t>(registers[rb])
    cdef uint32_t result = a if b == 0 else a % b
    registers[rd] = <uint64_t>chi(<uint64_t>result, <uint8_t>4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t rem_s_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC196: 32-bit signed remainder."""
    cdef int64_t a = <int64_t>(registers[ra])
    cdef int64_t b = <int64_t>(registers[rb])
    if a == -2147483648 and b == -1:  # -(2**31) and -1
        registers[rd] = 0
    else:
        registers[rd] = z_inv(smod(a, b), 8)
    return <uint32_t>0xFFFFFFFF

# 64-bit arithmetic operations  
cdef inline uint32_t  add_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC200: 64-bit addition."""
    registers[rd] = <uint64_t>(registers[ra] + registers[rb])
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  sub_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC201: 64-bit subtraction."""
    cdef uint64_t result = <uint64_t>(registers[ra] - registers[rb])
    registers[rd] = result
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  mul_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC202: 64-bit multiplication."""
    cdef uint64_t result = <uint64_t>(registers[ra] * registers[rb]) % (2**64)
    registers[rd] = result
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  div_u_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC203: 64-bit unsigned division."""
    cdef uint64_t a = registers[ra]
    cdef uint64_t b = registers[rb]
    if b == 0:
        registers[rd] = 0xFFFFFFFFFFFFFFFF  # 2**64 - 1
    else:
        registers[rd] = a // b  # Native unsigned division
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  div_s_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC204: 64-bit signed division."""
    cdef uint64_t a = registers[ra]
    cdef uint64_t b = registers[rb]
    if b == 0:
        registers[rd] = 0xFFFFFFFFFFFFFFFF  # 2**64 - 1
    else:
        # Handle signed division with proper overflow check
        if <int64_t>a == -9223372036854775808LL and <int64_t>b == -1:  # -(2**63) and -1
            registers[rd] = a  # Return original value for overflow case
        else:
            registers[rd] = <uint64_t>(<int64_t>(<int64_t>a / <int64_t>b))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  rem_u_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC205: 64-bit unsigned remainder."""
    a = registers[ra]
    b = registers[rb]
    registers[rd] = a if b == 0 else a % b
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  rem_s_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC206: 64-bit signed remainder."""
    a = <int64_t>registers[ra]
    b = <int64_t>registers[rb]
    if a == -(2**31) and b == -1:
        registers[rd] = 0
    else:
        registers[rd] = z_inv(smod(a, b), 8)
    return <uint32_t>0xFFFFFFFF

# Shift operations
cdef inline uint32_t  shlo_l_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC197: 32-bit logical left shift."""
    cdef uint32_t value = <uint32_t>(registers[ra])
    cdef uint32_t shift = <uint32_t>(registers[rb] & 31)
    cdef uint32_t result = value << shift
    registers[rd] = <uint64_t>chi(<uint64_t>result, <uint8_t>4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_r_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC198: 32-bit logical right shift."""
    cdef uint32_t value = <uint32_t>(registers[ra])
    cdef uint32_t shift = <uint32_t>(registers[rb] & 31)
    cdef uint32_t result = value >> shift
    registers[rd] = <uint64_t>chi(<uint64_t>result, <uint8_t>4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shar_r_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC199: 32-bit arithmetic shift right."""
    cdef int64_t signed_value = <int32_t>registers[ra]
    cdef uint32_t shift = <uint32_t>(registers[rb] & 31)
    cdef int64_t result = signed_value >> shift
    registers[rd] = <uint64_t>(result)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_l_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC207: 64-bit logical shift left."""
    cdef uint64_t value = registers[ra]
    cdef uint64_t shift = registers[rb] & 63
    registers[rd] = value << shift
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shlo_r_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC208: 64-bit logical shift right."""
    cdef uint64_t value = registers[ra]
    cdef uint64_t shift = registers[rb] & 63
    registers[rd] = value >> shift
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  shar_r_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC209: 64-bit arithmetic shift right."""
    cdef int64_t value = <int64_t>registers[ra]
    cdef uint64_t shift = registers[rb] & 63
    cdef int64_t result = value >> shift
    registers[rd] = z_inv(result, 8)
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

# Multiplication upper bits
cdef inline uint32_t  mul_upper_s_s(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC213: Signed multiplication upper 64 bits."""
    cdef int64_t signed_a = <int64_t>registers[ra]
    cdef int64_t signed_b = <int64_t>registers[rb]
    registers[rd] = <uint64_t>(signed_a * signed_b)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  mul_upper_u_u(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC214: Unsigned multiplication upper 64 bits."""
    registers[rd] = (
        int(registers[ra]) * int(registers[rb])
    ) // 2**64
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  mul_upper_s_u(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC215: Signed-unsigned multiplication upper 64 bits."""
    registers[rd] = z_inv(
        z(int(registers[ra]), 8) * int(registers[rb]) // 2**64, 8
    )

    return <uint32_t>0xFFFFFFFF

# Comparison operations
cdef inline uint32_t  set_lt_u(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC216: Set less than unsigned."""
    registers[rd] = int(registers[ra] < registers[rb])
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  set_lt_s(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC217: Set less than signed."""
    registers[rd] = int(<int64_t>registers[ra] < <int64_t>registers[rb])
    return <uint32_t>0xFFFFFFFF

# Conditional move operations
cdef inline uint32_t  cmov_iz(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC218: Conditional move if zero."""
    if registers[rb] == 0:
        registers[rd] = registers[ra]
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  cmov_nz(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC219: Conditional move if not zero."""
    if registers[rb] != 0:
        registers[rd] = registers[ra]
    return <uint32_t>0xFFFFFFFF

# Rotation operations
cdef inline uint32_t  rot_l_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC220: 64-bit rotate left."""
    cdef uint64_t value = registers[ra]
    cdef uint64_t shift = registers[rb] & 63
    registers[rd] = (value << shift) | (value >> (64 - shift))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  rot_l_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC221: 32-bit rotate left."""
    cdef uint32_t value = <uint32_t>(registers[ra])
    cdef uint32_t shift = <uint32_t>(registers[rb] & 31)
    cdef uint32_t result = (value << shift) | (value >> (32 - shift))
    registers[rd] = <uint64_t>chi(<uint64_t>result, <uint8_t>4)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  rot_r_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC222: 64-bit rotate right."""
    cdef uint64_t value = registers[ra]
    cdef uint64_t shift = registers[rb] & 63
    registers[rd] = (value >> shift) | (value << (64 - shift))
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  rot_r_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC223: 32-bit rotate right."""
    cdef uint32_t value = <uint32_t>(registers[ra])
    cdef uint32_t shift = <uint32_t>(registers[rb] & 31)
    cdef uint32_t result = (value >> shift) | (value << (32 - shift))
    registers[rd] = <uint64_t>chi(<uint64_t>result, <uint8_t>4)
    return <uint32_t>0xFFFFFFFF

# Inverted bitwise operations
cdef inline uint32_t  and_inv(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC224: Bitwise AND with inverted rb."""
    cdef uint64_t result = registers[ra] & (~registers[rb])
    registers[rd] = result
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  or_inv(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC225: Bitwise OR with inverted rb."""
    cdef uint64_t result = registers[ra] | (~registers[rb])
    registers[rd] = result
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  xnor(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC226: Bitwise XNOR (XOR with inverted result)."""
    cdef uint64_t result = ~(registers[ra] ^ registers[rb])
    registers[rd] = result
    return <uint32_t>0xFFFFFFFF

# Min/max operations
cdef inline uint32_t  max_op(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC227: Maximum signed."""
    cdef int64_t a = <int64_t>registers[ra]
    cdef int64_t b = <int64_t>registers[rb]
    cdef uint64_t result = <uint64_t>(a if a > b else b)
    registers[rd] = result
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  max_u(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC228: Maximum unsigned."""
    cdef uint64_t a = registers[ra]
    cdef uint64_t b = registers[rb]
    cdef uint64_t result = a if a > b else b
    registers[rd] = result
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  min_op(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC229: Minimum signed."""
    cdef int64_t a = <int64_t>registers[ra]
    cdef int64_t b = <int64_t>registers[rb]
    cdef uint64_t result = <uint64_t>(a if a < b else b)
    registers[rd] = result
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  min_u(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC230: Minimum unsigned."""
    cdef uint64_t a = registers[ra]
    cdef uint64_t b = registers[rb]
    cdef uint64_t result = a if a < b else b
    registers[rd] = result
    return <uint32_t>0xFFFFFFFF


cdef class CyInstructionsWArgs3Reg(CyTable):
    """
    Cython optimized instruction table for instructions with 3 register arguments.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract 3 register indices from program bytes using C struct.
        Returns InstructionProps struct with ra/rb as sources, rd as destination.
        """
        cdef InstructionProps props
        cdef uint8_t byte_val = program.zeta[program_counter + 1]
        
        props.ra = clamp_12(byte_val & 0x0F)  # Lower 4 bits
        props.rb = clamp_12(byte_val >> 4)    # Upper 4 bits  
        props.rd = clamp_12(program.zeta[program_counter + 2])    # Third register
        props.vx = 0  # Not used in 3-register instructions
        props.vy = 0  # Not used in 3-register instructions
        
        return props

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE


# Prebuilt table (opcode -> CyTableEntry) - This is a large table with many opcodes
cdef dict TABLE = {}
cdef CyTableEntry _e

# 32-bit arithmetic operations (190-199)
_e = CyTableEntry(); _e.fn = add_32_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[190] = _e
_e = CyTableEntry(); _e.fn = sub_32_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[191] = _e
_e = CyTableEntry(); _e.fn = mul_32_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[192] = _e
_e = CyTableEntry(); _e.fn = div_u_32_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[193] = _e
_e = CyTableEntry(); _e.fn = div_s_32_fn; _e.gas_cost = 1; _e.is_terminating = False; TABLE[194] = _e
_e = CyTableEntry(); _e.fn = rem_u_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[195] = _e
_e = CyTableEntry(); _e.fn = rem_s_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[196] = _e
_e = CyTableEntry(); _e.fn = shlo_l_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[197] = _e
_e = CyTableEntry(); _e.fn = shlo_r_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[198] = _e
_e = CyTableEntry(); _e.fn = shar_r_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[199] = _e

# 64-bit arithmetic operations (200-209)
_e = CyTableEntry(); _e.fn = add_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[200] = _e
_e = CyTableEntry(); _e.fn = sub_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[201] = _e
_e = CyTableEntry(); _e.fn = mul_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[202] = _e
_e = CyTableEntry(); _e.fn = div_u_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[203] = _e
_e = CyTableEntry(); _e.fn = div_s_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[204] = _e
_e = CyTableEntry(); _e.fn = rem_u_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[205] = _e
_e = CyTableEntry(); _e.fn = rem_s_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[206] = _e
_e = CyTableEntry(); _e.fn = shlo_l_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[207] = _e
_e = CyTableEntry(); _e.fn = shlo_r_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[208] = _e
_e = CyTableEntry(); _e.fn = shar_r_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[209] = _e

# Bitwise operations (210-212)
_e = CyTableEntry(); _e.fn = and_op; _e.gas_cost = 1; _e.is_terminating = False; TABLE[210] = _e
_e = CyTableEntry(); _e.fn = xor_op; _e.gas_cost = 1; _e.is_terminating = False; TABLE[211] = _e
_e = CyTableEntry(); _e.fn = or_op; _e.gas_cost = 1; _e.is_terminating = False; TABLE[212] = _e

# Multiplication upper bits (213-215)
_e = CyTableEntry(); _e.fn = mul_upper_s_s; _e.gas_cost = 1; _e.is_terminating = False; TABLE[213] = _e
_e = CyTableEntry(); _e.fn = mul_upper_u_u; _e.gas_cost = 1; _e.is_terminating = False; TABLE[214] = _e
_e = CyTableEntry(); _e.fn = mul_upper_s_u; _e.gas_cost = 1; _e.is_terminating = False; TABLE[215] = _e

# Comparison operations (216-217)
_e = CyTableEntry(); _e.fn = set_lt_u; _e.gas_cost = 1; _e.is_terminating = False; TABLE[216] = _e
_e = CyTableEntry(); _e.fn = set_lt_s; _e.gas_cost = 1; _e.is_terminating = False; TABLE[217] = _e

# Conditional move operations (218-219)
_e = CyTableEntry(); _e.fn = cmov_iz; _e.gas_cost = 1; _e.is_terminating = False; TABLE[218] = _e
_e = CyTableEntry(); _e.fn = cmov_nz; _e.gas_cost = 1; _e.is_terminating = False; TABLE[219] = _e

# Rotation operations (220-223)
_e = CyTableEntry(); _e.fn = rot_l_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[220] = _e
_e = CyTableEntry(); _e.fn = rot_l_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[221] = _e
_e = CyTableEntry(); _e.fn = rot_r_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[222] = _e
_e = CyTableEntry(); _e.fn = rot_r_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[223] = _e

# Inverted bitwise operations (224-226)
_e = CyTableEntry(); _e.fn = and_inv; _e.gas_cost = 1; _e.is_terminating = False; TABLE[224] = _e
_e = CyTableEntry(); _e.fn = or_inv; _e.gas_cost = 1; _e.is_terminating = False; TABLE[225] = _e
_e = CyTableEntry(); _e.fn = xnor; _e.gas_cost = 1; _e.is_terminating = False; TABLE[226] = _e

# Min/max operations (227-230)
_e = CyTableEntry(); _e.fn = max_op; _e.gas_cost = 1; _e.is_terminating = False; TABLE[227] = _e
_e = CyTableEntry(); _e.fn = max_u; _e.gas_cost = 1; _e.is_terminating = False; TABLE[228] = _e
_e = CyTableEntry(); _e.fn = min_op; _e.gas_cost = 1; _e.is_terminating = False; TABLE[229] = _e
_e = CyTableEntry(); _e.fn = min_u; _e.gas_cost = 1; _e.is_terminating = False; TABLE[230] = _e
