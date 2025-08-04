"""Common constants shared across PVM implementations."""

# Z_A — PVM dynamic address alignment factor. See equation A.18
PVM_ADDR_ALIGNMENT = 2

# Z_I — PVM program init input data size. See A.7
PVM_INIT_DATA_SIZE = 2**24

# Z_P — PVM memory page size. See equation 4.24
PVM_MEMORY_PAGE_SIZE = 2**12

# Z_Z — PVM init zone size. See A.7
PVM_INIT_ZONE_SIZE = 2**16

# 4 GB PVM Memory Size
PVM_MEMORY_TOTAL_SIZE = 4 * (1024**3)

# Z_R — Number of registers in the standard PVM
REGISTER_COUNT = 13
