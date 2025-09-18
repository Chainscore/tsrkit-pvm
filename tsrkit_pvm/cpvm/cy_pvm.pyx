# cython: boundscheck=False, wraparound=False, nonecheck=False, cdivision=True, language_level=3
# cython: profile=False, embedsignature=True

"""
Cython optimized PVM interpreter execution loop.

This is the main entry point for the Cython-optimized PVM execution.
Provides identical API to the interpreter version but with C-level performance.
"""

cimport cython
from libc.stdint cimport int32_t, int64_t, uint32_t, uint64_t
from typing import Any, List, Tuple, Union

from .cy_program cimport CyProgram
from .cy_memory cimport CyMemory
from .mapper cimport CyInstMapper, inst_map
from tsrkit_pvm.common.status import OUT_OF_GAS, PAGE_FAULT, PANIC, ExecutionStatus, PvmError, CONTINUE
from .mapper cimport inst_map

cdef class CyInterpreter:
    """
    Cython-optimized PVM interpreter.
    
    This class provides the same interface as the original Interpreter class
    but with Cython optimizations for the critical execution loop.
    """
    
    @classmethod
    def execute(
        cls,
        program: CyProgram,
        program_counter: int,
        gas: int,
        registers: List[int],
        memory: CyMemory,
        logger: Union[Any, None] = None,
    ):
        cdef int64_t remaining_gas = gas
        cdef int32_t pc = program_counter

        cdef uint64_t reg_arr[13]
        for i in range(13):
            reg_arr[i] = registers[i]
        
        status = None
        
        # Debug logging at start
        if logger:
            logger.debug(
                "Starting PVM execution",
                registers=registers,
                inst_size=len(program.instruction_set),
                initial_pc=program_counter,
                initial_gas=gas,
                program_size=len(program.zeta),
            )

        status, pc, remaining_gas = _execute_internal(program, pc, remaining_gas, reg_arr, memory)

        if logger:
            logger.info(
                "PVM result",
                final_pc=pc,
                gas_remaining=remaining_gas,
                registers=reg_arr,
                memory=memory,
            )

        # Convert C integers back to Python for return
        cdef list py_registers = []
        for i in range(13):
            py_registers.append(int(reg_arr[i]))
        
        return status, int(pc), int(remaining_gas), py_registers, memory


cdef tuple _execute_internal(
    CyProgram program,
    int32_t program_counter,
    int64_t gas,
    uint64_t *registers,
    CyMemory memory,
):
    """
    Internal Cython-only execution method for maximum performance.
    This bypasses Python object creation and uses C types throughout.
    """
    cdef int64_t remaining_gas = gas
    cdef int32_t pc = program_counter
    cdef int32_t gas_cost
    cdef bint should_break = False
    cdef tuple result
    cdef object status = None
    
    # Main execution loop - this is the critical hot path
    while not should_break:
        try:
            # Execute instruction using optimized mapper
            result, gas_cost = inst_map.process_instruction(program, pc, registers, memory)
            status, pc = result

            remaining_gas -= gas_cost

            if remaining_gas < 0:
                status = OUT_OF_GAS
                should_break = True
                continue

            # Optimize status checking
            if status == ExecutionStatus.HALT:
                should_break = True
                continue
            elif status == ExecutionStatus.HOST:
                should_break = True
                continue

        except PvmError as e:
            if e.code == PANIC:
                status = PANIC
                should_break = True
            elif e.code == ExecutionStatus.PAGE_FAULT:
                status = PAGE_FAULT(e.code.value.register)
                should_break = True
            else:
                raise e
        except Exception as e:
            raise e

    return status, pc, remaining_gas

