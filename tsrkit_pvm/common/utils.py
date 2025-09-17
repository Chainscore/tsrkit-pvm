"""Common utilities shared across PVM implementations."""

import operator
from .constants import PVM_INIT_ZONE_SIZE, PVM_MEMORY_PAGE_SIZE
from typing import List, Union, Any

_PVM_MEMORY_PAGE_SHIFT = 12  # log2(PVM_MEMORY_PAGE_SIZE) = log2(4096) = 12
_PVM_INIT_ZONE_SHIFT = 16   # log2(PVM_INIT_ZONE_SIZE) = log2(65536) = 16
_PVM_MEMORY_PAGE_MASK = PVM_MEMORY_PAGE_SIZE - 1  # 4095 for alignment checks


def clamp_12(val: int) -> int:
    """Optimized clamp to range [0, 12] - faster than min(12, val)."""
    return val if val <= 12 else 12

def clamp_4(val: int) -> int:
    """Optimized clamp to range [0, 4] - faster than min(4, val)."""
    return val if val <= 4 else 4

def clamp_4_max0(val: int) -> int:
    """Optimized clamp to range [0, 4] with max(0, val) - faster than min(4, max(0, val))."""
    if val <= 0:
        return 0
    return val if val <= 4 else 4


# --- Memory Utils --- #
def total_page_size(blob_len: int) -> int:
    """Calculate total page size needed for a blob."""
    # use bit operations instead of division/multiplication
    # ceil(blob_len / PVM_MEMORY_PAGE_SIZE) * PVM_MEMORY_PAGE_SIZE
    # = ((blob_len + PVM_MEMORY_PAGE_SIZE - 1) >> _PVM_MEMORY_PAGE_SHIFT) << _PVM_MEMORY_PAGE_SHIFT
    return ((blob_len + _PVM_MEMORY_PAGE_MASK) >> _PVM_MEMORY_PAGE_SHIFT) << _PVM_MEMORY_PAGE_SHIFT


def total_zone_size(blob_len: int) -> int:
    """Calculate total zone size needed for a blob."""
    # use bit operations instead of division/multiplication
    zone_mask = PVM_INIT_ZONE_SIZE - 1
    return ((blob_len + zone_mask) >> _PVM_INIT_ZONE_SHIFT) << _PVM_INIT_ZONE_SHIFT


def get_pages(start_index: int, length: int) -> list[int]:
    """Get list of page numbers spanning a memory range."""
    # use bit shift instead of division
    start = start_index >> _PVM_MEMORY_PAGE_SHIFT
    end_index = start_index + max(length, 1) - 1
    end = end_index >> _PVM_MEMORY_PAGE_SHIFT
    return list(range(start, end + 1))


# --- Inst utils --- #
def chi(value: int, n: int) -> int:
    """Make value (of size n) an unbounded integer."""
    # Handle edge case where n is 0
    if n <= 0:
        return value
    
    # Optimized: pre-calculate bit shifts and avoid repeated power calculations
    bit_pos = (n << 3) - 1  # 8 * n - 1
    multiplier = (1 << 64) - (1 << (n << 3))  # 2**64 - 2 ** (8 * n)
    return value + ((value >> bit_pos) * multiplier)


def z(x: int, n: int) -> int:
    """Z function - convert unsigned integers to signed."""
    # Handle edge case where n is 0
    if n <= 0:
        return x
    
    # Optimized: use bit operations instead of power calculations
    threshold = 1 << ((n << 3) - 1)  # 2 ** (8 * n - 1)
    if x < threshold:
        return x
    else:
        return x - (1 << (n << 3))  # x - 2 ** (8 * n)


def z_inv(x: int, n: int) -> int:
    """Z_inv function."""
    # Handle edge case where n is 0
    if n <= 0:
        return x
    
    # Optimized: avoid repeated type conversions and use bit operations
    bit_count = n << 3  # 8 * n
    modulus = 1 << bit_count  # 2 ** (8 * n)
    return (modulus + x) & (modulus - 1)  # equivalent to % 2**(8*n)


BYTE_TO_BITS = [tuple(((b >> i) & 1) for i in range(8)) for b in range(256)]
BYTES_TO_BYTE = {bytes(bits): b for b, bits in enumerate(BYTE_TO_BITS)}

def b(value: int, byte_size: int, is_reversed: bool = False) -> List[int]:
    """Convert integer to list of bits."""
    if byte_size <= 0:
        return []

    bit_count = byte_size << 3
    out = [0] * bit_count  # preallocate list of correct size

    if not is_reversed:
        for byte_index in range(byte_size):
            byte = (value >> (byte_index * 8)) & 0xFF
            bits = BYTE_TO_BITS[byte]
            base = byte_index * 8
            out[base:base+8] = bits
    else:
        for byte_index in range(byte_size):
            byte = (value >> (byte_index * 8)) & 0xFF
            bits = BYTE_TO_BITS[byte][::-1]
            base = bit_count - (byte_index+1)*8
            out[base:base+8] = bits

    return out

def b_inv(value: List[int], is_reversed: bool = False) -> int:
    """Convert list of bits to integer."""
    # avoid repeated list operations and use enumerate
    if is_reversed:
        # Create a reversed copy instead of modifying the original
        value = value[::-1]
    
    result = 0
    # Use enumerate to avoid repeated indexing
    for i, bit in enumerate(value):
        if bit:  # Only add if bit is 1, skip multiplication by 0
            result += 1 << i  # Use bit shift instead of 2**i
    return result


# Pre-computed comparison operations lookup table for performance
_COMPARISON_OPS = {
    'eq' : operator.eq,
    'ne' : operator.ne,
    'lt' : operator.lt,
    'le' : operator.le,
    'gt' : operator.gt,
    'ge' : operator.ge,
    'and': operator.and_,
    'or' : operator.or_,
    'xor': operator.xor,
}

def compare(a: Union[int, bool], b: Union[int, bool], op: str) -> Any:
    """Compare two values using the specified operation."""
    # Use lookup table for common operations (much faster than getattr)
    if op in _COMPARISON_OPS:
        return _COMPARISON_OPS[op](a, b)
    
    # Fallback to dynamic lookup for less common operations
    return getattr(a, f"__{op}__")(b)

def compare_bits_vectorized(bits_a: List[Union[int, bool]], bits_b: List[int], op: str) -> List[int]:
    """Vectorized bit comparison for 64-bit operations - much faster than loop."""
    if op == 'and':
        return [a & b for a, b in zip(bits_a, bits_b)]
    elif op == 'or':
        return [a | b for a, b in zip(bits_a, bits_b)]
    elif op == 'xor':
        return [a ^ b for a, b in zip(bits_a, bits_b)]
    elif op == 'eq':
        return [int(a == b) for a, b in zip(bits_a, bits_b)]
    elif op == 'ne':
        return [int(a != b) for a, b in zip(bits_a, bits_b)]
    elif op == 'lt':
        return [int(a < b) for a, b in zip(bits_a, bits_b)]
    elif op == 'le':
        return [int(a <= b) for a, b in zip(bits_a, bits_b)]
    elif op == 'gt':
        return [int(a > b) for a, b in zip(bits_a, bits_b)]
    elif op == 'ge':
        return [int(a >= b) for a, b in zip(bits_a, bits_b)]
    else:
        # Fallback to individual comparisons for unknown operations
        return [compare(a, b, op) for a, b in zip(bits_a, bits_b)]


def rtz(x: int) -> int:
    """Round towards zero."""
    # use int() which truncates towards zero for both positive and negative
    return int(x)


def smod(a: int, b: int) -> int:
    """Signed modulo operation."""
    if b == 0:
        return a
    # avoid repeated abs() calls and unnecessary division
    abs_a = abs(a)
    abs_b = abs(b)
    sign_a = 1 if a >= 0 else -1
    return sign_a * (abs_a % abs_b)
