from typing import Tuple
from tsrkit_types import U64, TypedArray
from tsrkit_pvm.recompiler.program import Program
from tsrkit_pvm.recompiler.assembler.caller import create_caller
from tsrkit_pvm.recompiler.fn_alloc import allocate_executable_memory
from tsrkit_pvm.recompiler.vm_context import VMContext
import time


class PVM:

    @staticmethod
    def execute(
        program: Program,
        program_counter: int,
        registers: list[int],
        gas: int
    ) -> Tuple[None, int, int, list]:
        start_time_ns = time.time_ns()
        # Assemble and store the program code 
        msn_code, msn_pc_offset = program.assemble(program_counter)
        print(f"Machine code {msn_code.hex()} | Start offset {msn_pc_offset}")
        code_buf, code_pointer = allocate_executable_memory(msn_code)

        # Vm Context
        vm_ctx = VMContext(regs=TypedArray[U64, 13]([U64(i) for i in registers]), gas=U64(gas))
        vm_buf, vm_pointer = vm_ctx.store()

        print("INITIAL VM", VMContext.decode(vm_buf))
    
        # Create callable function
        func = create_caller(code_pointer + msn_pc_offset, vm_pointer)
        
        # Execute the compiled code
        print("Executing compiled PVM code...")
        result = func()
        print(f"Execution taken {(time.time_ns() - start_time_ns) / (10**6)} ms")
        
        vm_result = VMContext.decode(vm_buf)
        print("POST VM", vm_result)
        
        # Create callable function
        # Clean up
        code_buf.close()
        vm_buf.close()
        return None, 0, vm_result.gas, vm_result.regs
