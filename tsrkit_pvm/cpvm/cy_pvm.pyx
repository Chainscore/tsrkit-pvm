# cython: boundscheck=False, wraparound=False, nonecheck=False, cdivision=True, language_level=3
# cython: profile=False, embedsignature=True, linetrace=False
# cython: initializedcheck=False, overflowcheck=False, infer_types=True
# cython: optimize.unpack_method_calls=True

"""
Cython optimized PVM interpreter execution loop.

This is the main entry point for the Cython-optimized PVM execution.
Provides identical API to the interpreter version but with C-level performance.
"""

cimport cython
from libc.stdint cimport int32_t, int64_t, uint32_t, uint64_t, uint8_t
from typing import Any, List, Tuple, Union

from libc.stdint cimport uint8_t, int32_t
from .cy_program cimport CyProgram
from .cy_memory cimport CyMemory
from .mapper cimport CyInstMapper, inst_map
from .cy_status cimport OUT_OF_GAS, PAGE_FAULT, PVM_HALT, PVM_PANIC, PVM_PAGE_FAULT, PVM_OUT_OF_GAS, PVM_HOST, CyStatus, CONTINUE, PVM_CONTINUE
from .cy_status cimport PvmExit
from ..common.status import ExecutionStatus, HALT, PANIC, OUT_OF_GAS as EXEC_OUT_OF_GAS, CONTINUE as EXEC_CONTINUE, HOST, PAGE_FAULT as EXEC_PAGE_FAULT
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
                program_size=program.zeta_len,
            )

        status, pc, remaining_gas = _execute_internal(program, pc, remaining_gas, reg_arr, memory)
        if logger:
            logger.debug(
                "PVM result",
                final_pc=pc,
                gas_remaining=remaining_gas,
                registers=[int(reg_arr[i]) for i in range(13)],
                memory=memory,
            )

        # Convert C integers back to Python for return
        cdef list py_registers = []
        for i in range(13):
            py_registers.append(int(reg_arr[i]))
        
        # Convert CyStatus to Python ExecutionStatus for compatibility
        cdef object execution_status = None
        # Convert CyStatus to Python ExecutionStatus based on status code
        if status.code == PVM_HALT:
            execution_status = HALT
        elif status.code == PVM_PANIC:
            execution_status = PANIC
        elif status.code == PVM_OUT_OF_GAS:
            execution_status = EXEC_OUT_OF_GAS
        elif status.code == PVM_CONTINUE:
            execution_status = EXEC_CONTINUE
        elif status.code == PVM_HOST:
            # For HOST status, create with register value
            execution_status = HOST(status.register)
        elif status.code == PVM_PAGE_FAULT:
            # For PAGE_FAULT status, create with register value
            execution_status = EXEC_PAGE_FAULT(status.register)
        else:
            # Default to HALT for unknown status codes
            execution_status = HALT
        
        return execution_status, int(pc), int(remaining_gas), py_registers, memory


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
    cdef CyStatus status = CONTINUE
    cdef int status_code = 0
    
    while not should_break:
        try:
            # Execute instruction using optimized mapper (this will handle nogil internally)
            pc, gas_cost = inst_map.process_instruction(program, pc, registers, memory)
            remaining_gas -= gas_cost

            if remaining_gas < 0:
                status = OUT_OF_GAS
                should_break = True
                continue

        except PvmExit as e:
            if e.code < 5:
                should_break = True
                status.code = e.code 
                status.register = e.register
                remaining_gas -= e.gas_cost
                pc = e.next_pc
            else:
                raise e

    return status, pc, remaining_gas

