import ctypes
import _ctypes  # type: ignore


class ProgramData(ctypes.Structure):
    """Register state at time of segfault"""

    _fields_ = [
        ("r8", ctypes.c_uint64),
        ("r9", ctypes.c_uint64),
        ("r10", ctypes.c_uint64),
        ("r11", ctypes.c_uint64),
        ("r12", ctypes.c_uint64),
        ("r13", ctypes.c_uint64),
        ("r14", ctypes.c_uint64),
        ("r15", ctypes.c_uint64),
        ("rdi", ctypes.c_uint64),
        ("rsi", ctypes.c_uint64),
        ("rbp", ctypes.c_uint64),
        ("rbx", ctypes.c_uint64),
        ("rdx", ctypes.c_uint64),
        ("rax", ctypes.c_uint64),
        ("rcx", ctypes.c_uint64),
        ("rsp", ctypes.c_uint64),
        ("rip", ctypes.c_uint64),
        ("eflags", ctypes.c_uint64),
        ("si_data", ctypes.c_uint64),
        ("status", ctypes.c_int8),
    ]

    def vm_regs(self):
        """Return registers as per our mapping @vm_context"""
        return [
            self.rdi,
            self.rax,
            self.rsi,
            self.rbx,
            self.rdx,
            self.rbp,
            self.r8,
            self.r9,
            self.r10,
            self.r11,
            self.r12,
            self.r13,
            self.r14,
        ]

    def vm_fault_pc(self, start_addr: int, asm_trace: list[int]) -> int:
        """Binary search thru our assembled code and calculate native (rip) -> pvm address"""
        # TODO:
        return 0

    def vm_fault_addr(self):
        """si_addr - r15"""
        return self.si_data - self.r15
