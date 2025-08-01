from typing import Tuple

from tsrkit_types import TypedArray
from tsrkit_pvm.recompiler.memory import GuestMemory
from tsrkit_pvm.recompiler.program import Program
from tsrkit_pvm.recompiler.assembler.caller import (
    create_caller,
)
from tsrkit_pvm.recompiler.fn_alloc import allocate_executable_memory
from tsrkit_pvm.recompiler.vm_context import VMContext
from tsrkit_pvm.recompiler.sig_handler import (
    run_code, 
    cleanup_sig_state,
    init_sig_handlers
)
import time


class PVM:
    @staticmethod
    def execute(
        program: Program,
        memory: GuestMemory,
        program_counter: int,
        registers: list[int],
        gas: int,
        logger = None
    ) -> Tuple[None, int, int, list]:
        
        start_time_ns = time.time_ns()
        code_buf, code_pointer = allocate_executable_memory(program.msn_code)

        # VM Context
        vm_ctx = VMContext([program.pvm_to_msn_index(j)+code_pointer for j in program.jump_table], registers, gas)
        vm_pointer, vm_size = vm_ctx.store(memory)

        # Create callable function - pass memory.offset (guest memory pointer)
        addr, _ = create_caller(
            code_pointer + program.pvm_to_msn_index(program_counter), 
            memory.offset, 
            vm_size
        )
        # Install safe signal handler
        init_sig_handlers()
        
        # Execute the compiled code with segfault protection
        if logger: logger.debug(f"Assmbling completed | Time {(time.time_ns() - start_time_ns) / (10**6)} ms")
        asm_time_ns = time.time_ns()
        
        # Activate syscall handler for PVM syscalls during execution
        try:
            status, updated_regs, pg_data = run_code(
                addr, 
                vm_ctx, 
                vm_pointer, 
                code_pointer +  program.halt_offset, 
                logger
            )
            
            # NOTE: This is a temporary handler for `sbrk` - remove this once the instruction is removed
            while (
                    status._value_.name == "host" and 
                    status._value_.register == 2**64 - 1 and 
                    pg_data
            ):
                # We need imm, Calc the PVM instruction against current rip 
                pvm_pc = program.msn_to_pvm_index(pg_data.rip - code_pointer)
                imm = program.instruction_set[pvm_pc+1]
                rd, ra = min(12, imm % 16), min(12, imm // 16)
                # Pages to add 
                req = updated_regs[ra]
                updated_regs[rd] = vm_ctx.heap_start + req

                memory.alter_accessibility(vm_ctx.heap_start, req)

                # Create callable function - pass memory.offset (guest memory pointer)
                vm_ctx = VMContext(vm_ctx.jump_table, updated_regs, gas, heap_start=(vm_ctx.heap_start+req))
                _, _ = vm_ctx.store(memory)
                addr, _ = create_caller(pg_data.rip, memory.offset, vm_size)
                # Run from last return 
                status, updated_regs, pg_data = run_code(
                    addr, 
                    vm_ctx, 
                    vm_pointer, 
                    code_pointer +  program.halt_offset, 
                    logger
                )
        finally:
            cleanup_sig_state()

        if logger: logger.debug(f"Execution completed | Time: {(time.time_ns() - asm_time_ns) / (10**6)} ms")
        
        gas = int(VMContext.from_pointer(vm_pointer, len(program.jump_table)).gas)

        # Adjust overflow
        if status._value_.name == "out-of-gas":
            print("Ran OOG", gas)
            gas -= 2**32

        if logger: logger.debug(f"Status: {status._value_} | Registers: {updated_regs} | Gas: {gas}")

        # Create callable function
        # Clean up
        code_buf.close()
        memory.buf.close()
        return status, 0, gas, updated_regs

def sbrk(registers: list[int], memory: GuestMemory):
    print("sbrking", registers)
    return registers
