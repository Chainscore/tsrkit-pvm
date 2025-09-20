# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
"""Ultra-optimized C-level utilities for maximum PVM performance."""

cimport cython
from libc.stdint cimport uint8_t, uint16_t, uint32_t, uint64_t, int8_t, int16_t, int32_t, int64_t
from libc.stdlib cimport malloc, free
from libc.string cimport memset, memcpy
from libc.math cimport floor, ceil

# Import constants from the constants module
cdef uint32_t PVM_MEMORY_PAGE_SIZE = 4096
cdef uint32_t PVM_INIT_ZONE_SIZE = 65536
cdef uint32_t PVM_MEMORY_PAGE_SHIFT = 12  # log2(4096)
cdef uint32_t PVM_INIT_ZONE_SHIFT = 16    # log2(65536)
cdef uint32_t PVM_MEMORY_PAGE_MASK = 4095  # 4096 - 1

# ─────────────────── Ultra-fast C-level lookup tables ───────────────────
cdef uint8_t[256][8] BYTE_TO_BITS_LUT
cdef uint8_t[256] BYTES_TO_BYTE_LUT

# Initialize lookup tables at module load
cdef void _init_lookup_tables():
    """Initialize C-level lookup tables for maximum performance."""
    cdef uint32_t b, i
    
    # Build BYTE_TO_BITS lookup table
    for b in range(256):
        for i in range(8):
            BYTE_TO_BITS_LUT[b][i] = (b >> i) & 1
            
    # Build BYTES_TO_BYTE reverse lookup
    for b in range(256):
        BYTES_TO_BYTE_LUT[b] = b

# Initialize tables
_init_lookup_tables()

# Memory utilities - ultra-fast C implementations
cdef uint32_t total_page_size(uint32_t blob_len) nogil except? 0:
    """Calculate total page size needed for a blob - matches Python version exactly."""
    return ((blob_len + PVM_MEMORY_PAGE_MASK) >> PVM_MEMORY_PAGE_SHIFT) << PVM_MEMORY_PAGE_SHIFT

cdef uint32_t total_zone_size(uint32_t blob_len) nogil except? 0:
    """Calculate total zone size needed for a blob - matches Python version exactly."""
    cdef uint32_t zone_mask = PVM_INIT_ZONE_SIZE - 1
    return ((blob_len + zone_mask) >> PVM_INIT_ZONE_SHIFT) << PVM_INIT_ZONE_SHIFT

cdef list get_pages(uint32_t start_index, uint32_t length):
    """Get list of page numbers spanning a memory range - matches Python version exactly."""
    cdef uint32_t start = start_index >> PVM_MEMORY_PAGE_SHIFT
    cdef uint32_t max_length = length if length > 0 else 1  # max(length, 1)
    cdef uint32_t end_index = start_index + max_length - 1
    cdef uint32_t end = end_index >> PVM_MEMORY_PAGE_SHIFT
    cdef uint32_t i
    
    # Pre-allocate list with exact size for efficiency
    cdef uint32_t page_count = end - start + 1
    cdef list result = [0] * page_count
    
    # Fill the list efficiently
    for i in range(page_count):
        result[i] = start + i
    
    return result

# Bit manipulation utilities - C-level performance with inline optimization
@cython.cfunc
@cython.inline
cdef int64_t chi(uint64_t value, uint8_t n) nogil except? -1:
    """Make value (of size n) an unbounded integer - ultra-fast inline version."""
    if n <= 0: return value
    if n >= 8: return <int64_t>value  # Already unbounded
    cdef uint8_t bits = n << 3  # 8 * n
    cdef uint64_t sign_bit = 1ULL << (bits - 1)
    return <int64_t>value if (value & sign_bit) == 0 else <int64_t>(value | (~((1ULL << bits) - 1)))

@cython.cfunc
@cython.inline
cdef int64_t z(uint64_t x, uint8_t n) nogil except? -1:
    """Z function - convert unsigned to signed - ultra-fast inline version."""
    if n <= 0 or n >= 8: return <int64_t>x  # Edge cases
    cdef uint8_t bits = n << 3  # 8 * n
    cdef uint64_t mask = (1ULL << bits) - 1
    cdef uint64_t sign_bit = 1ULL << (bits - 1)
    return <int64_t>((x & mask) ^ sign_bit) - sign_bit  # Proper two's complement

@cython.cfunc
@cython.inline
cdef uint64_t z_inv(int64_t x, uint8_t n) nogil except? 0:
    """Z_inv function - convert signed to unsigned - ultra-fast inline version."""
    if n <= 0 or n >= 8: return <uint64_t>x  # Edge cases
    return <uint64_t>x & ((1ULL << (n << 3)) - 1)  # Just mask to n bytes

# Bit operations - interface compatible with utils.py
cdef list b(uint64_t value, uint8_t byte_size, bint is_reversed = False):
    """Convert integer to list of bits - maximally optimized version."""
    if byte_size <= 0:
        return []

    cdef uint32_t bit_count = byte_size << 3
    cdef uint32_t i
    
    # Pre-allocate result list with exact size  
    result = [0] * bit_count
    
    # Special cases for ultra-common bit sizes with manual unrolling
    if byte_size == 1:  # 8 bits - extremely common case
        if not is_reversed:
            result[0] = value & 1
            result[1] = (value >> 1) & 1
            result[2] = (value >> 2) & 1
            result[3] = (value >> 3) & 1
            result[4] = (value >> 4) & 1
            result[5] = (value >> 5) & 1
            result[6] = (value >> 6) & 1
            result[7] = (value >> 7) & 1
        else:
            result[0] = (value >> 7) & 1
            result[1] = (value >> 6) & 1
            result[2] = (value >> 5) & 1
            result[3] = (value >> 4) & 1
            result[4] = (value >> 3) & 1
            result[5] = (value >> 2) & 1
            result[6] = (value >> 1) & 1
            result[7] = value & 1
        return result
    elif byte_size == 4:  # 32 bits - also very common
        if not is_reversed:
            for i in range(32):
                result[i] = (value >> i) & 1
        else:
            for i in range(32):
                result[i] = (value >> (31 - i)) & 1
        return result
    elif byte_size <= 8:  # Up to 64 bits
        if not is_reversed:
            for i in range(bit_count):
                result[i] = (value >> i) & 1
        else:
            for i in range(bit_count):
                result[i] = (value >> (bit_count - 1 - i)) & 1
        return result
    
    # For larger sizes (rare), use byte-wise processing with lookup table
    cdef uint32_t byte_index, bit_index, base
    cdef uint8_t byte_val
    
    if not is_reversed:
        for byte_index in range(byte_size):
            byte_val = (value >> (byte_index << 3)) & 0xFF
            base = byte_index << 3
            # Use lookup table for 8-bit chunks
            for bit_index in range(8):
                result[base + bit_index] = BYTE_TO_BITS_LUT[byte_val][bit_index]
    else:
        for byte_index in range(byte_size):
            byte_val = (value >> (byte_index << 3)) & 0xFF
            base = bit_count - ((byte_index + 1) << 3)
            for bit_index in range(8):
                result[base + bit_index] = BYTE_TO_BITS_LUT[byte_val][7 - bit_index]
    
    return result

cdef uint64_t b_inv(list bits, bint is_reversed = False):
    """Convert list of bits to integer - maximally optimized for hot path."""
    if not bits:
        return 0
    
    cdef uint32_t bit_count = len(bits)
    cdef uint64_t result = 0
    cdef uint32_t i
    
    if bit_count == 0:
        return 0
        
    # Ultra-fast path for most common cases
    if bit_count == 8:  # Single byte - extremely common
        if not is_reversed:
            # Manual unroll for maximum speed
            result = bits[0] | (bits[1] << 1) | (bits[2] << 2) | (bits[3] << 3) | \
                     (bits[4] << 4) | (bits[5] << 5) | (bits[6] << 6) | (bits[7] << 7)
        else:
            result = bits[7] | (bits[6] << 1) | (bits[5] << 2) | (bits[4] << 3) | \
                     (bits[3] << 4) | (bits[2] << 5) | (bits[1] << 6) | (bits[0] << 7)
        return result
    elif bit_count == 32:  # 32-bit values - also common
        if not is_reversed:
            for i in range(32):
                if bits[i]:
                    result |= 1ULL << i
        else:
            for i in range(32):
                if bits[31 - i]:
                    result |= 1ULL << i
        return result
    elif bit_count <= 64:  # Fits in uint64_t - optimized path
        if not is_reversed:
            for i in range(bit_count):
                if bits[i]:
                    result |= 1ULL << i
        else:
            for i in range(bit_count):
                if bits[bit_count - 1 - i]:
                    result |= 1ULL << i
        return result
    
    # Fallback for very large bit arrays (rare)
    if is_reversed:
        for i in range(bit_count):
            if bits[bit_count - 1 - i]:
                result += 1ULL << i
    else:
        for i in range(bit_count):
            if bits[i]:
                result += 1ULL << i
    
    return result

# Math utilities - optimized C implementations  
cdef int64_t rtz(double x) nogil except? -1:
    """Round towards zero - matches Python version exactly."""
    return <int64_t>x  # C cast truncates towards zero like Python int()

cdef int64_t smod(int64_t a, int64_t b) nogil except? -1:
    """Signed modulo operation - matches Python version exactly."""
    if b == 0:
        return a
    # Match Python version logic exactly
    cdef int64_t abs_a = a if a >= 0 else -a
    cdef int64_t abs_b = b if b >= 0 else -b
    cdef int64_t sign_a = 1 if a >= 0 else -1
    return sign_a * (abs_a % abs_b)

# Clamp functions - branchless C implementations with inline optimization
@cython.cfunc
@cython.inline
cdef uint8_t clamp_12(uint8_t val) nogil except? 255:
    """Clamp to range [0, 12] - ultra-fast inline branchless version."""
    return val if val <= 12 else 12

@cython.cfunc
@cython.inline
cdef uint8_t clamp_4(uint8_t val) nogil except? 255:
    """Clamp to range [0, 4] - ultra-fast inline branchless version."""
    return val if val <= 4 else 4

@cython.cfunc
@cython.inline
cdef uint8_t clamp_4_max0(int8_t val) nogil except? 255:
    """Clamp to range [0, 4] with max(0, val) - ultra-fast inline version."""
    if val <= 0:
        return 0
    return <uint8_t>val if val <= 4 else 4

# ═══════════════════════ FAST BYTE CONVERSION UTILITIES ═══════════════════════
# Ultra-fast C-level byte conversion functions to replace expensive Python operations

cdef bytes uint64_to_bytes_le(uint64_t value, uint8_t num_bytes):
    """Convert uint64 to little-endian bytes - ultra-fast C implementation."""
    cdef uint8_t[8] buffer
    cdef uint8_t i
    
    for i in range(8):
        buffer[i] = <uint8_t>((value >> (i * 8)) & 0xFF)
    
    return buffer[:num_bytes]

cdef bytes uint32_to_bytes_le(uint32_t value, uint8_t num_bytes):
    """Convert uint32 to little-endian bytes - ultra-fast C implementation."""
    cdef uint8_t[4] buffer
    cdef uint8_t i
    
    for i in range(4):
        buffer[i] = <uint8_t>((value >> (i * 8)) & 0xFF)
    
    return buffer[:num_bytes]

cdef bytes uint16_to_bytes_le(uint16_t value, uint8_t num_bytes):
    """Convert uint16 to little-endian bytes - ultra-fast C implementation."""
    cdef uint8_t[2] buffer
    cdef uint8_t i
    
    for i in range(2):
        buffer[i] = <uint8_t>((value >> (i * 8)) & 0xFF)
    
    return buffer[:num_bytes]

cdef bytes uint8_to_bytes_le(uint8_t value, uint8_t num_bytes):
    """Convert uint8 to little-endian bytes - ultra-fast C implementation."""
    cdef uint8_t[1] buffer
    buffer[0] = value
    return buffer[:num_bytes]

cdef uint64_t bytes_to_uint64_le(bytes data):
    """Convert little-endian bytes to uint64 - ultra-fast C implementation."""
    cdef uint64_t result = 0
    cdef uint8_t i
    cdef uint8_t data_len = len(data)
    cdef const uint8_t* data_ptr = <const uint8_t*>data
    
    for i in range(min(data_len, 8)):
        result |= (<uint64_t>data_ptr[i]) << (i * 8)
    
    return result

cdef uint32_t bytes_to_uint32_le(bytes data):
    """Convert little-endian bytes to uint32 - ultra-fast C implementation."""
    cdef uint32_t result = 0
    cdef uint8_t i
    cdef uint8_t data_len = len(data)
    cdef const uint8_t* data_ptr = <const uint8_t*>data
    
    for i in range(min(data_len, 4)):
        result |= (<uint32_t>data_ptr[i]) << (i * 8)
    
    return result

cdef uint16_t bytes_to_uint16_le(bytes data):
    """Convert little-endian bytes to uint16 - ultra-fast C implementation."""
    cdef uint16_t result = 0
    cdef uint8_t i
    cdef uint8_t data_len = len(data)
    cdef const uint8_t* data_ptr = <const uint8_t*>data
    
    for i in range(min(data_len, 2)):
        result |= (<uint16_t>data_ptr[i]) << (i * 8)
    
    return result

cdef uint8_t bytes_to_uint8_le(bytes data):
    """Convert little-endian bytes to uint8 - ultra-fast C implementation."""
    if len(data) > 0:
        return (<const uint8_t*>data)[0]
    return 0
