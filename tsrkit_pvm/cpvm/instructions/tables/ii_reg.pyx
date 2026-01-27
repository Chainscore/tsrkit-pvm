# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, int64_t, uint64_t, uint8_t
from ...cy_status cimport CONTINUE
from ...cy_utils cimport clamp_12, z, z_inv, b
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t, InstructionProps
from ...cy_memory cimport CyMemory, ACC_WRITE
from ...cy_program cimport CyProgram

# ----------------------------#
# ---- C helper functions ----#
# ----------------------------#
cdef inline uint32_t _count_set_bits_c(uint64_t val):
    """Fast bit counting using Brian Kernighan's algorithm."""
    cdef uint32_t count = 0
    while val:
        val &= val - 1  # Clear lowest set bit
        count += 1
    return count

cdef inline uint32_t _leading_zeros_c(uint64_t val, uint32_t bitsize):
    """Count leading zeros with C-level bit operations."""
    if val == 0:
        return bitsize
    
    cdef uint32_t count = 0
    cdef uint64_t mask = 1ULL << (bitsize - 1)
    
    while (val & mask) == 0:
        count += 1
        mask >>= 1
        
    return count

cdef inline uint32_t _trailing_zeros_c(uint64_t val, uint32_t bitsize):
    """Count trailing zeros with C-level bit operations."""
    if val == 0:
        return bitsize
        
    cdef uint32_t count = 0
    while (val & 1) == 0:
        count += 1
        val >>= 1
        
    return count


cdef inline uint32_t  move_reg(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC100: Move value from register ra to register rd."""
    registers[rd] = registers[ra]
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t sbrk(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, 
                uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC101: Expand heap by ra bytes and store old break in rd."""
    cdef int64_t req = registers[ra]  # bytes requested
    memory._alter_accessibility_c(memory.heap_break, req, ACC_WRITE)
    
    # Store old heap break in destination register (before updating it)
    cdef uint64_t old_heap_break = memory.heap_break
    registers[rd] = old_heap_break
    
    # Update heap break
    memory.heap_break = memory.heap_break + req
    
    return <uint32_t>0xFFFFFFFF

# Bit counting instructions with C-level optimizations
cdef inline uint32_t  count_set_bits_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC102: Count set bits in 64-bit value."""
    registers[rd] = _count_set_bits_c(registers[ra] & 0xFFFFFFFFFFFFFFFF)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  count_set_bits_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC103: Count set bits in 32-bit value."""
    registers[rd] = _count_set_bits_c(registers[ra] & 0xFFFFFFFF)
    return <uint32_t>0xFFFFFFFF

# Leading zero counting with C optimizations
cdef inline uint32_t  leading_zero_bits_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC104: Count leading zero bits in 64-bit value."""
    registers[rd] = _leading_zeros_c(registers[ra] & 0xFFFFFFFFFFFFFFFF, 64)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  leading_zero_bits_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC105: Count leading zero bits in 32-bit value."""
    registers[rd] = _leading_zeros_c(registers[ra] & 0xFFFFFFFF, 32)
    return <uint32_t>0xFFFFFFFF

# Trailing zero counting with C optimizations  
cdef inline uint32_t  trailing_zero_bits_64(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC106: Count trailing zero bits in 64-bit value."""
    registers[rd] = _trailing_zeros_c(registers[ra] & 0xFFFFFFFFFFFFFFFF, 64)
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  trailing_zero_bits_32(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC107: Count trailing zero bits in 32-bit value."""
    registers[rd] = _trailing_zeros_c(registers[ra] & 0xFFFFFFFF, 32)
    return <uint32_t>0xFFFFFFFF

# Sign extension instructions
cdef inline uint32_t  sign_extend_8(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC108: Sign extend 8-bit value to 64-bit."""
    cdef uint64_t val = registers[ra] & 0xFF  # Get low 8 bits
    # Check if sign bit (bit 7) is set
    if val & 0x80:
        # Sign extend by setting upper 56 bits to 1
        registers[rd] = val | 0xFFFFFFFFFFFFFF00
    else:
        # Zero extend
        registers[rd] = val
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  sign_extend_16(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC109: Sign extend 16-bit value to 64-bit."""
    cdef uint64_t val = registers[ra] & 0xFFFF  # Get low 16 bits
    # Check if sign bit (bit 15) is set
    if val & 0x8000:
        # Sign extend by setting upper 48 bits to 1
        registers[rd] = val | 0xFFFFFFFFFFFF0000
    else:
        # Zero extend
        registers[rd] = val
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  zero_extend_16(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC110: Zero extend 16-bit value to 64-bit."""
    cdef uint64_t val = registers[ra] % (2**16)
    registers[rd] = val
    return <uint32_t>0xFFFFFFFF

cdef inline uint32_t  reverse_bytes(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC111: Reverse byte order of 64-bit value."""
    cdef uint64_t val = registers[ra]
    cdef uint64_t result = 0
    
    # Fast byte reversal using C bit operations
    result |= ((val & 0x00000000000000FF) << 56)
    result |= ((val & 0x000000000000FF00) << 40)
    result |= ((val & 0x0000000000FF0000) << 24)
    result |= ((val & 0x00000000FF000000) << 8)
    result |= ((val & 0x000000FF00000000) >> 8)
    result |= ((val & 0x0000FF0000000000) >> 24)
    result |= ((val & 0x00FF000000000000) >> 40)
    result |= ((val & 0xFF00000000000000) >> 56)
    
    registers[rd] = result
    return <uint32_t>0xFFFFFFFF

cdef class CyInstructionsWArgs2Reg(CyTable):
    """
    Cython optimized instruction table for instructions with 2 register arguments.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract register indices from program bytes.
        Returns InstructionProps struct where ra is source, rd is destination, others are 0.
        """
        # Extract byte value using C-style operations for speed
        cdef uint8_t byte_val = program.zeta[program_counter + 1]
        cdef uint8_t rd_val = clamp_12(<uint8_t>(byte_val & 0x0F))  # Lower 4 bits (destination)
        cdef uint8_t ra_val = clamp_12(<uint8_t>(byte_val >> 4))    # Upper 4 bits (source)
        
        # Return InstructionProps struct
        cdef InstructionProps props
        props.vx = 0  # Not used in register-only instructions
        props.vy = 0  # Not used in register-only instructions
        props.ra = ra_val  # Source register
        props.rb = 0  # Not used in 2-register instructions
        props.rd = rd_val  # Destination register
        
        return props

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = move_reg; _e.gas_cost = 1; _e.is_terminating = False; TABLE[100] = _e
_e = CyTableEntry(); _e.fn = sbrk; _e.gas_cost = 1; _e.is_terminating = False; TABLE[101] = _e
_e = CyTableEntry(); _e.fn = count_set_bits_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[102] = _e
_e = CyTableEntry(); _e.fn = count_set_bits_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[103] = _e
_e = CyTableEntry(); _e.fn = leading_zero_bits_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[104] = _e
_e = CyTableEntry(); _e.fn = leading_zero_bits_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[105] = _e
_e = CyTableEntry(); _e.fn = trailing_zero_bits_64; _e.gas_cost = 1; _e.is_terminating = False; TABLE[106] = _e
_e = CyTableEntry(); _e.fn = trailing_zero_bits_32; _e.gas_cost = 1; _e.is_terminating = False; TABLE[107] = _e
_e = CyTableEntry(); _e.fn = sign_extend_8; _e.gas_cost = 1; _e.is_terminating = False; TABLE[108] = _e
_e = CyTableEntry(); _e.fn = sign_extend_16; _e.gas_cost = 1; _e.is_terminating = False; TABLE[109] = _e
_e = CyTableEntry(); _e.fn = zero_extend_16; _e.gas_cost = 1; _e.is_terminating = False; TABLE[110] = _e
_e = CyTableEntry(); _e.fn = reverse_bytes; _e.gas_cost = 1; _e.is_terminating = False; TABLE[111] = _e
