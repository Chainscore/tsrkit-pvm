from typing import Tuple
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
        # Assemble and store the program code
        msn_code, msn_pc_offset, jump_table, halt_addr, panic_addr = program.assemble(program_counter, logger)
        if logger: logger.debug(f"Machine code {msn_code.hex()}... | Start offset {msn_pc_offset} | Jump Table {jump_table}")
        code_buf, code_pointer = allocate_executable_memory(msn_code)

        # VM Context
        # jump_table.reverse()
        vm_ctx = VMContext([j+code_pointer for j in jump_table], registers, gas)
        vm_pointer, vm_size = vm_ctx.store(memory)

        # Create callable function - pass memory.offset (guest memory pointer)
        addr, _, _ = create_caller(code_pointer + msn_pc_offset, memory.offset, vm_size)
        # Install safe signal handler
        init_sig_handlers()
        
        # Execute the compiled code with segfault protection
        if logger: logger.debug(f"Assmbling completed | Time {(time.time_ns() - start_time_ns) / (10**6)} ms")
        asm_time_ns = time.time_ns()
        
        # Activate syscall handler for PVM syscalls during execution
        try:
            success, registers_final = run_code(addr, vm_ctx, vm_pointer, code_pointer +  halt_addr, logger)
        finally:
            cleanup_sig_state()

        if logger: logger.debug(f"Execution completed | Time: {(time.time_ns() - asm_time_ns) / (10**6)} ms")
        
        gas = int(VMContext.from_pointer(vm_pointer, len(jump_table)).gas)

        # Adjust overflow
        if success._value_.name == "out-of-gas":
            gas -= 2**32

        if logger: logger.debug(f"Status: {success._value_.name} | Registers: {registers_final} | Gas: {gas}")

        # Create callable function
        # Clean up
        code_buf.close()
        memory.buf.close()
        return success, 0, gas, registers_final
