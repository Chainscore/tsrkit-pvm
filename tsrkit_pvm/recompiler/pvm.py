from typing import Tuple, ClassVar, Optional
import importlib.util
from tsrkit_pvm.core.ipvm import PVM
from tsrkit_pvm.recompiler.assembler.inst_map import inst_map
from tsrkit_pvm.recompiler.memory import REC_Memory
from tsrkit_pvm.recompiler.program import REC_Program
from tsrkit_pvm.recompiler.segwrap.sig_handler import ProgramData
from tsrkit_pvm.recompiler.vm_context import VMContext, TEMP_REG
from tsrkit_pvm.recompiler.assembler.utils import (
    load_all_regs,
    pop_all_regs,
    push_all_regs,
    save_all_regs,
)
from tsrkit_asm import (
    PyAssembler,
    RegMem,
    Reg,
)
import ctypes
import mmap
import os

# Load libc for mprotect
if os.uname().sysname == "Darwin":
    libc = ctypes.CDLL("libc.dylib", use_errno=True)
else:
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
libc.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
libc.mprotect.restype = ctypes.c_int

from ..common.status import PANIC, HALT, PAGE_FAULT, HOST, OUT_OF_GAS, ExecutionStatus

# NOTE: Python's signal mod can only handle signals at high lvl
# Its handlers run on main thread only
# C's sigaction provides a better low level handler
try:
    spec = importlib.util.find_spec("tsrkit_pvm.recompiler.segwrap._segwrap")
    if spec is None or spec.origin is None:
        raise ImportError("recompiler segwrap extension is not built")

    _segwrap_path = spec.origin
    segwrap: Optional[ctypes.CDLL] = ctypes.CDLL(_segwrap_path)

    if (
        hasattr(segwrap, "initialize")
        and hasattr(segwrap, "run_code")
        and hasattr(segwrap, "get_program_status")
        and hasattr(segwrap, "cleanup")
    ):
        _segwrap_available = True
    else:
        _segwrap_available = False
        print("Warning: segwrap library loaded but missing expected symbols")

except (ImportError, OSError, Exception) as e:
    segwrap = None
    _segwrap_available = False


class Recompiler(PVM):
    """Recompiler mode of PVM"""
    
    _signal_handlers_initialized: ClassVar[bool] = False  # Class variable to track initialization

    @classmethod
    def execute(
        cls,
        program: REC_Program,
        program_counter: int,
        gas: int,
        registers: list[int],
        memory: REC_Memory,
        logger=None,
    ) -> Tuple[ExecutionStatus, int, int, list, REC_Memory]:

        if not program.msn_code:
            program.assemble(logger=logger)
            
        # Ensure type is bytes for mypy
        assert program.msn_code is not None, "assemble() must set msn_code"

        code_buf, code_pointer = cls.allocate_executable_memory(program.msn_code)
        
        # Track all allocated buffers for cleanup
        allocated_buffers = [code_buf]

        # VM Context
        vm_ctx = VMContext(
            [program.pvm_to_msn_index(j) + code_pointer for j in program.jump_table],
            registers,
            gas,
            heap_start=memory.heap_start,
        )
        vm_pointer, vm_size = vm_ctx.store(memory)

        # Create callable function - pass memory.offset (guest memory pointer)
        addr, caller_buf = cls.create_caller(
            code_pointer + program.pvm_to_msn_index(program_counter), memory.offset
        )
        allocated_buffers.append(caller_buf)
        # Install safe signal handler (only once per process)
        cls.init_sig_handlers()

        # Activate syscall handler for PVM syscalls during execution
        try:
            status, updated_regs, pg_data = cls.run_code(
                addr, vm_ctx, vm_pointer, code_pointer + program.halt_offset, logger
            )

        except Exception as e:
            raise ValueError(f"Page Fault {e}")
        finally:
            cls.cleanup_sig_state()

        fault_offset = pg_data.rip - code_pointer
        final_pc = program.msn_to_pvm_index(fault_offset)
        if status == PANIC:
            final_pc = program.msn_to_pvm_index(program.panic_offset)

        updated_vm_ctx = VMContext.from_pointer(vm_pointer, len(program.jump_table))
        gas = int(updated_vm_ctx.gas)  # gas is already an int
        if status in (PANIC, HALT) and updated_vm_ctx.ret_addr:
            final_pc = int(updated_vm_ctx.ret_addr) - 1

        # Adjust overflow
        if status._value_.name == "out-of-gas":
            gas -= 2**32
            final_pc = program.msn_to_pvm_index(pg_data.si_data - code_pointer)

        # Clean up allocated memory buffers
        for buf in allocated_buffers:
            try:
                buf.close()
            except:
                pass  # Ignore cleanup errors
        
        return status, final_pc, gas, updated_regs, memory

    @classmethod
    def create_caller(cls, code_pointer: int, mem_pointer: int):
        """Create a caller function that executes generated code."""
        asm = PyAssembler()

        # RCX -> code pointer, R15 -> guest memory base while generated code runs.
        asm.mov_imm64(TEMP_REG, code_pointer)
        asm.push(Reg.r15)
        asm.mov_imm64(Reg.r15, mem_pointer)  # Base pointer to linear PVM memory

        # ----------------------------------------------------------
        # Guest-register mapping
        # ----------------------------------------------------------
        push_all_regs(asm)
        load_all_regs(asm)

        # call the generated program
        asm.call(RegMem.Reg(TEMP_REG))

        # ----------------------------------------------------------
        # Store back the results
        # ----------------------------------------------------------
        save_all_regs(asm)
        pop_all_regs(asm)
        asm.pop(Reg.r15)

        asm.ret()

        thunk = asm.finalize()
        buf, addr = cls.allocate_executable_memory(thunk)
        return addr, buf

    @classmethod
    def allocate_executable_memory(cls, code: bytes, logger=None):
        """Allocate RWX memory and copy machine code"""
        size = len(code)
        # Allocate RW memory first
        page_size = mmap.PAGESIZE
        alloc_size = (size + page_size - 1) & ~(page_size - 1)
        
        try:
            buf = mmap.mmap(-1, alloc_size, access=mmap.ACCESS_WRITE)
            buf.write(code)

            # Change protection to RX
            addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
            prot_rx = mmap.PROT_READ | mmap.PROT_EXEC
            # Align address to page boundary for mprotect
            aligned_addr = addr & ~(page_size - 1)
            res = libc.mprotect(
                ctypes.c_void_p(aligned_addr), ctypes.c_size_t(alloc_size), prot_rx
            )
            if res != 0:
                err = ctypes.get_errno()
                buf.close()  # Clean up on failure
                raise OSError(err, "mprotect failed to set RX permissions")

            if logger:
                logger.debug(f"Executable of size {size} stored at {addr}")
            return buf, addr
        except Exception as e:
            # Clean up on any failure
            if 'buf' in locals():
                try:
                    buf.close()
                except:
                    pass
            raise e

    @classmethod
    def init_sig_handlers(cls, logger = None):
        """Install the C signal handlers (only once per process)"""
        if cls._signal_handlers_initialized:
            return  # Already initialized
        
        if not _segwrap_available or segwrap is None:
            if logger: logger.warning("Warning: segwrap library not available, signal handlers disabled")
            cls._signal_handlers_initialized = True
            return
            
        result = segwrap.initialize()
        if result != 0:
            # If we get error -3, it's likely a seccomp restriction (containers, etc.)
            # For now, we'll allow this to continue but log a warning
            if result == -3:
                if logger: 
                    logger.warning(
                        "Failed to install seccomp filter (error -3). PVM syscall handling may not work properly in restricted environments. This is expected in containers or sandboxed environments.",
                    )
                # Mark as initialized even if seccomp failed, to avoid repeated attempts
                cls._signal_handlers_initialized = True
                return  # Continue without seccomp
            else:
                raise OSError(f"Failed to install signal handler: {result}")
        
        cls._signal_handlers_initialized = True

    @classmethod
    def run_code(
        cls, addr: int, vm_ctx: VMContext, vm_pointer: int, halt_addr: int, logger=None
    ) -> tuple[ExecutionStatus, list[int], ProgramData]:
        """
        Run code at given address with segfault protection.

        Returns:
            (status, return_value, registers_on_fault)
            - status: Execution status (PANIC, HALT, PAGE_FAULT, HOST, OUT_OF_GAS)
            - updated_regs: Final register state after execution
            - pg_data: Program data on fault (if any)
        """
        ret_val = ctypes.c_uint64(0)
        
        if not _segwrap_available or segwrap is None:
            # Fallback when segwrap is not available
            print("Warning: segwrap not available, returning PANIC status")
            pg_data = ProgramData()
            pg_data.rip = ret_val
            return PANIC, vm_ctx.regs, pg_data
            
        result = segwrap.run_code(ctypes.c_uint64(addr), ctypes.byref(ret_val))
        pg_data = ProgramData()

        if result == 0:
            # Success - no segfault
            pg_data.rip = ret_val
            updated_vm_ctx = VMContext.from_pointer(vm_pointer, len(vm_ctx.jump_table))
            return PANIC, updated_vm_ctx.regs, pg_data  # regs is now a plain list
        else:
            # Segfault occurred - get register state
            if segwrap.get_program_status(ctypes.byref(pg_data)) == 0:
                if logger:
                    logger.debug(
                        f"""Faulted! {pg_data.status}
                            \t SI \t {pg_data.si_data} 
                            \t RIP \t {pg_data.rip} 
                            \t R15 \t {pg_data.r15} 
                            \t RCX \t {pg_data.rcx}
                    """
                    )
                if pg_data.status == 0:
                    updated_vm_ctx = VMContext.from_pointer(
                        vm_pointer, len(vm_ctx.jump_table)
                    )
                    return (
                        HOST(pg_data.si_data),
                        updated_vm_ctx.regs,  # regs is now a plain list
                        pg_data,
                    )
                elif pg_data.status == 1:
                    return (
                        PAGE_FAULT(pg_data.vm_fault_addr()),
                        pg_data.vm_regs(),
                        pg_data,
                    )
                elif pg_data.status == 2:
                    if pg_data.si_data == halt_addr:
                        return HALT, pg_data.vm_regs(), pg_data
                    else:
                        return OUT_OF_GAS, pg_data.vm_regs(), pg_data

        pg_data.rip = ret_val
        return PANIC, [0] * len(pg_data.vm_regs()), pg_data

    @classmethod
    def cleanup_sig_state(cls):
        """Clean up signal handlers and reset initialization state"""
        if _segwrap_available and segwrap is not None:
            segwrap.cleanup()
        cls._signal_handlers_initialized = False  # Allow re-initialization
