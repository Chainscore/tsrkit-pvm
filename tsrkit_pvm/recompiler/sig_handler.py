import ctypes
import os
from .vm_context import VMContext
from ..interpreter.status import PANIC, HALT, PAGE_FAULT, HOST, OUT_OF_GAS

# NOTE: Python's signal mod can only handle signals at high lvl
# Its handlers run on main thread only
# C's sigaction provides a better low level handler
_lib_path = os.path.join(os.path.dirname(__file__), "libsegwrap.so")
lib = ctypes.CDLL(_lib_path)


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


def init_sig_handlers():
    """Install the C signal handlers"""
    result = lib.initialize()
    if result != 0:
        raise OSError(f"Failed to install signal handler: {result}")


def run_code(
    addr: int, vm_ctx: VMContext, vm_pointer: int, halt_addr: int, logger=None
) -> tuple[int, list[int], ProgramData | None]:
    """
    Run code at given address with segfault protection.

    Returns:
        (success, return_value, registers_on_fault)
        - success: True if no segfault, False if segfaulted
        - return_value: Return value from function (if success)
        - registers_on_fault: Register state at fault (if not success)
    """
    ret_val = ctypes.c_uint64(0)
    result = lib.run_code(ctypes.c_uint64(addr), ctypes.byref(ret_val))

    if result == 0:
        # Success - no segfault
        updated_vm_ctx = VMContext.from_pointer(vm_pointer, len(vm_ctx.jump_table))
        return PANIC, [int(r) for r in updated_vm_ctx.regs], None
    else:
        # Segfault occurred - get register state
        regs = ProgramData()
        if lib.get_program_status(ctypes.byref(regs)) == 0:
            if logger:
                logger.debug(
                    f"Faulted! \n\t Status \t {regs.status} \n\t SI Data \t {regs.si_data} \n\t RIP \t {regs.rip} \n\t Fault \t {regs.si_data} \n\t R15 \t {regs.r15} \n\t RCX \t {regs.rcx}"
                )
            if regs.status == 0:
                updated_vm_ctx = VMContext.from_pointer(
                    vm_pointer, len(vm_ctx.jump_table)
                )
                return HOST(regs.si_data), [int(r) for r in updated_vm_ctx.regs], regs
            elif regs.status == 1:
                return PAGE_FAULT(regs.si_data), regs.vm_regs(), regs
            elif regs.status == 2:
                if regs.si_data == halt_addr:
                    return HALT, regs.vm_regs(), regs
                else:
                    return OUT_OF_GAS, regs.vm_regs(), regs
            else:
                PANIC, [0] * len(regs.vm_regs()), None
        else:
            return PANIC, [0] * len(regs.vm_regs()), None


def cleanup_sig_state():
    lib.cleanup()
