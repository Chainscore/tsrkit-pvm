# cython: language_level=3
"""Cython header file for optimized utility functions."""

from libc.stdint cimport uint8_t, uint16_t, uint32_t, uint64_t, int8_t, int16_t, int32_t, int64_t
from libc.stdlib cimport malloc, free
from libc.string cimport memset, memcpy

# ─────────────────────── C-level optimized functions ───────────────────────

# Memory utilities - ultra-fast C implementations
cdef uint32_t total_page_size(uint32_t blob_len) nogil except? 0
cdef uint32_t total_zone_size(uint32_t blob_len) nogil except? 0
cdef list get_pages(uint32_t start_index, uint32_t length)

cdef int64_t chi(uint64_t value, uint8_t n) nogil except? -1
cdef int64_t z(uint64_t x, uint8_t n) nogil except? -1
cdef uint64_t z_inv(int64_t x, uint8_t n) nogil except? 0

# Bit operations - interface compatible with utils.py
cdef list b(uint64_t value, uint8_t byte_size, bint is_reversed = ?)
cdef uint64_t b_inv(list bits, bint is_reversed = ?)

# Math utilities - optimized C implementations  
cdef int64_t rtz(double x) nogil except? -1
cdef int64_t smod(int64_t a, int64_t b) nogil except? -1

# Fast byte conversion utilities - C-level performance for memory ops
cdef bytes uint64_to_bytes_le(uint64_t value, uint8_t num_bytes) 
cdef bytes uint32_to_bytes_le(uint32_t value, uint8_t num_bytes)
cdef bytes uint16_to_bytes_le(uint16_t value, uint8_t num_bytes)
cdef bytes uint8_to_bytes_le(uint8_t value, uint8_t num_bytes)
cdef uint64_t bytes_to_uint64_le(bytes data)
cdef uint32_t bytes_to_uint32_le(bytes data)
cdef uint16_t bytes_to_uint16_le(bytes data)
cdef uint8_t bytes_to_uint8_le(bytes data)

cdef uint8_t clamp_12(uint8_t val) nogil except? 255
cdef uint8_t clamp_4(uint8_t val) nogil except? 255
cdef uint8_t clamp_4_max0(int8_t val) nogil except? 255

# Comparison operation codes for C-level lookup
cdef enum CmpOp:
    CMP_EQ = 0
    CMP_NE = 1
    CMP_LT = 2
    CMP_LE = 3
    CMP_GT = 4
    CMP_GE = 5
    CMP_AND = 6
    CMP_OR = 7
    CMP_XOR = 8

# Pre-computed lookup tables for ultra-fast operations
cdef uint8_t[256][8] BYTE_TO_BITS_LUT
cdef uint8_t[256] BYTES_TO_BYTE_LUT

# Initialization function
cdef void _init_lookup_tables()
