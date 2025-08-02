from typing import Tuple

from tsrkit_pvm.core.ipvm import PVM
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
import time
import ctypes
import mmap
import os

# Load libc for mprotect
if os.uname().sysname == "Darwin":
    libc = ctypes.CDLL("libc.dylib")
else:
    libc = ctypes.CDLL("libc.so.6")

from ..common.status import PANIC, HALT, PAGE_FAULT, HOST, OUT_OF_GAS, ExecutionStatus

# NOTE: Python's signal mod can only handle signals at high lvl
# Its handlers run on main thread only
# C's sigaction provides a better low level handler
_segwrap_path = os.path.join(os.path.dirname(__file__), "segwrap", "libsegwrap.so")
segwrap = ctypes.CDLL(_segwrap_path)


class Recompiler(PVM):
    """Recompiler mode of PVM"""

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
            program.assemble(logger)

        start_time_ns = time.time_ns()
        code_buf, code_pointer = cls.allocate_executable_memory(program.msn_code)

        # VM Context
        vm_ctx = VMContext(
            [program.pvm_to_msn_index(j) + code_pointer for j in program.jump_table],
            registers,
            gas,
        )
        vm_pointer, vm_size = vm_ctx.store(memory)

        # Create callable function - pass memory.offset (guest memory pointer)
        addr, _ = cls.create_caller(
            code_pointer + program.pvm_to_msn_index(program_counter),
            memory.offset,
            vm_size,
        )
        # Install safe signal handler
        cls.init_sig_handlers()

        # Execute the compiled code with segfault protection
        if logger:
            logger.debug(
                f"Assmbling completed | Time {(time.time_ns() - start_time_ns) / (10**6)} ms"
            )
        asm_time_ns = time.time_ns()

        # Activate syscall handler for PVM syscalls during execution
        try:
            status, updated_regs, pg_data = cls.run_code(
                addr, vm_ctx, vm_pointer, code_pointer + program.halt_offset, logger
            )

            # NOTE: This is a temporary handler for `sbrk` - remove this once the instruction is removed
            while (
                status._value_.name == "host"
                and status._value_.register == 2**64 - 1
                and pg_data
            ):
                # We need imm, Calc the PVM instruction against current rip
                pvm_pc = program.msn_to_pvm_index(pg_data.rip - code_pointer)
                imm = program.instruction_set[pvm_pc + 1]
                rd, ra = min(12, imm % 16), min(12, imm // 16)
                # Pages to add
                req = updated_regs[ra]
                updated_regs[rd] = vm_ctx.heap_start + req

                memory.alter_accessibility(vm_ctx.heap_start, req)

                # Create callable function - pass memory.offset (guest memory pointer)
                vm_ctx = VMContext(
                    vm_ctx.jump_table,
                    updated_regs,
                    gas,
                    heap_start=(vm_ctx.heap_start + req),
                )
                _, _ = vm_ctx.store(memory)
                addr, _ = cls.create_caller(pg_data.rip, memory.offset, vm_size)
                # Run from last return
                status, updated_regs, pg_data = cls.run_code(
                    addr, vm_ctx, vm_pointer, code_pointer + program.halt_offset, logger
                )
        except Exception as e:
            raise ValueError(f"Page Fault {e}")
        finally:
            cls.cleanup_sig_state()

        final_pc = program.msn_to_pvm_index(pg_data.rip - code_pointer)

        if logger:
            logger.debug(
                f"Execution completed | Time: {(time.time_ns() - asm_time_ns) / (10**6)} ms"
            )

        gas = int(VMContext.from_pointer(vm_pointer, len(program.jump_table)).gas)

        # Adjust overflow
        if status._value_.name == "out-of-gas":
            print("Ran OOG", gas)
            gas -= 2**32

        if logger:
            logger.debug(
                f"Status: {status._value_} | Registers: {updated_regs} | Gas: {gas}"
            )

        # Clean up
        code_buf.close()
        memory.buf.close()

        return status, final_pc, gas, updated_regs, memory
    
    @classmethod
    def create_caller(cls, code_pointer: int, mem_pointer: int, vm_size: int):
        """Create a caller function that executes generated code."""
        asm = PyAssembler()

        # RCX –> code pointer,  R15 –> pointer to VMContext struct
        asm.mov_imm64(TEMP_REG, code_pointer)
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

        if logger:
            logger.debug(f"Executable of size {size} stored at {addr}")
        return buf, addr
    
    @classmethod
    def init_sig_handlers(cls):
        """Install the C signal handlers"""
        result = segwrap.initialize()
        if result != 0:
            raise OSError(f"Failed to install signal handler: {result}")

    @classmethod
    def run_code(
        cls, 
        addr: int, 
        vm_ctx: VMContext, 
        vm_pointer: int, 
        halt_addr: int, 
        logger=None
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
        result = segwrap.run_code(ctypes.c_uint64(addr), ctypes.byref(ret_val))
        pg_data = ProgramData()

        if result == 0:
            # Success - no segfault
            pg_data.rip = ret_val
            updated_vm_ctx = VMContext.from_pointer(vm_pointer, len(vm_ctx.jump_table))
            return PANIC, [int(r) for r in updated_vm_ctx.regs], pg_data
        else:
            # Segfault occurred - get register state
            if segwrap.get_program_status(ctypes.byref(pg_data)) == 0:
                if logger:
                    logger.debug(
                        f"Faulted! \n\t Status \t {pg_data.status} \n\t SI Data \t {pg_data.si_data} \n\t RIP \t {pg_data.rip} \n\t Fault \t {pg_data.si_data} \n\t R15 \t {pg_data.r15} \n\t RCX \t {pg_data.rcx}"
                    )
                if pg_data.status == 0:
                    updated_vm_ctx = VMContext.from_pointer(
                        vm_pointer, len(vm_ctx.jump_table)
                    )
                    return HOST(pg_data.si_data), [int(r) for r in updated_vm_ctx.regs], pg_data
                elif pg_data.status == 1:
                    return PAGE_FAULT(pg_data.si_data), pg_data.vm_regs(), pg_data
                elif pg_data.status == 2:
                    if pg_data.si_data == halt_addr:
                        return HALT, pg_data.vm_regs(), pg_data
                    else:
                        return OUT_OF_GAS, pg_data.vm_regs(), pg_data
                    
        pg_data.rip = ret_val
        return PANIC, [0] * len(pg_data.vm_regs()), pg_data

    @classmethod
    def cleanup_sig_state(cls):
        segwrap.cleanup()


# Export Recompiler as PVM for backward compatibility
PVM = Recompiler
