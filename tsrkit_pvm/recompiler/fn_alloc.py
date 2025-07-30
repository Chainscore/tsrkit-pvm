import ctypes
import mmap
import os

# Load libc for mprotect
if os.uname().sysname == "Darwin":
    libc = ctypes.CDLL("libc.dylib")
else:
    libc = ctypes.CDLL("libc.so.6")


def allocate_executable_memory(code, logger = None):
    """Allocate RWX memory and copy machine code"""
    size = len(code)
    # Allocate RW memory first
    page_size = mmap.PAGESIZE
    alloc_size = (size + page_size - 1) & ~(page_size - 1)
    buf = mmap.mmap(-1, alloc_size, access=mmap.ACCESS_WRITE)
    buf.write(code)

    # Change protection to RX
    addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
    prot_rx = mmap.PROT_EXEC | mmap.ACCESS_WRITE
    # Align address to page boundary for mprotect
    aligned_addr = addr & ~(page_size - 1)
    res = libc.mprotect(
        ctypes.c_void_p(aligned_addr), ctypes.c_size_t(alloc_size), prot_rx
    )
    if res != 0:
        err = ctypes.get_errno()
        raise OSError(err, "mprotect failed to set RX permissions")

    if logger: logger.debug(f"Executable of size {size} stored at {addr}")
    return buf, addr
