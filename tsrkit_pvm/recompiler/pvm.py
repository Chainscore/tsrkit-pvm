from tsrkit_types import U64, TypedArray
from tsrkit_pvm.interpreter.program import Program
from tsrkit_pvm.recompiler.assembler.asm import assemble, create_callable_function
from tsrkit_pvm.recompiler.fn_alloc import allocate_executable_memory
from tsrkit_pvm.recompiler.vm_context import VMContext
import time

class PVM:

    @staticmethod
    def execute(
        program: Program,
        registers: TypedArray[U64, 4],
        gas: int
    ):
        start_time_ns = time.time_ns()
        # Assemble and store the program code 
        msn_code = assemble(program)
        print(f"Machine code:", msn_code.hex())
        code_buf, code_pointer = allocate_executable_memory(msn_code)

        # Vm Context
        vm_ctx = VMContext(regs=registers, gas=U64(gas))
        vm_buf, vm_pointer = vm_ctx.store()

        print("INITIAL VM", VMContext.decode(vm_buf))
    
        # Create callable function
        func = create_callable_function(code_pointer, vm_pointer)
        
        # Execute the compiled code
        print("Executing compiled PVM code...")
        result = func()
        print(f"Execution taken {(time.time_ns() - start_time_ns) / (10**6)} ms")

        print("POST VM", VMContext.decode(vm_buf))
        
        # Create callable function
        # Clean up
        code_buf.close()
        # vm_buf.close()
     
