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

from .cy_program import CyProgram
from .cy_memory import CyMemory
from tsrkit_pvm.common.status import OUT_OF_GAS, PAGE_FAULT, PANIC, ExecutionStatus, PvmError, CONTINUE
from .mapper import inst_map

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
        # Use C integers for performance-critical variables
        cdef int64_t remaining_gas = gas
        cdef int32_t pc = program_counter
        cdef int32_t gas_cost
        cdef bint should_break = False

        cdef uint64_t reg_arr[13]
        for i in range(13):
            reg_arr[i] = registers[i]
        
        # Keep status as Python object for compatibility
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

        # Main execution loop - this is the critical hot path
        while not should_break:
            try:
                # Execute instruction using optimized mapper
                result, gas_cost = inst_map.process_instruction(program, pc, reg_arr, memory)
                status, pc, _, memory = result

                remaining_gas -= gas_cost

                if remaining_gas < 0:
                    if logger:
                        logger.warning(
                            "PVM - OUT_OF_GAS",
                            final_pc=pc,
                            gas_deficit=abs(remaining_gas),
                        )
                    status = OUT_OF_GAS
                    should_break = True
                    continue

                # Optimize status checking
                if status == ExecutionStatus.HALT:
                    if logger:
                        logger.info(
                            "PVM - HALT",
                            final_pc=pc,
                            gas_remaining=remaining_gas,
                        )
                    should_break = True
                    continue
                elif status == ExecutionStatus.HOST:
                    if logger:
                        logger.debug(
                            "PVM - HOST",
                            pc=pc,
                            gas_remaining=remaining_gas,
                        )
                    should_break = True
                    continue

            except PvmError as e:
                if logger:
                    logger.error(
                        "PVM execution error",
                        error_message=str(e),
                        error_code=e.code,
                        pc=pc,
                        gas_remaining=remaining_gas,
                    )
                if e.code == PANIC:
                    status = PANIC
                    should_break = True
                elif e.code == ExecutionStatus.PAGE_FAULT:
                    status = PAGE_FAULT(e.code.value.register)
                    should_break = True
                else:
                    raise e
            except Exception as e:
                if logger:
                    logger.critical(
                        "Unexpected PVM execution error",
                        error=str(e),
                        error_type=type(e).__name__,
                        pc=pc,
                    )
                raise e

        if logger:
            logger.info(
                "PVM result",
                final_pc=pc,
                gas_remaining=remaining_gas,
                registers=reg_arr,
                memory=memory,
            )

        # Convert C integers back to Python for return
        return status, int(pc), int(remaining_gas), reg_arr, memory

