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

from tsrkit_pvm.interpreter.memory import INT_Memory
from tsrkit_pvm.interpreter.program import INT_Program
from tsrkit_pvm.common.status import OUT_OF_GAS, PAGE_FAULT, PANIC, ExecutionStatus, PvmError, CONTINUE
from .instructions.tables import ALL_CY_TABLES
from .mapper import CyInstMapper
from .cy_memory import CyMemory
import array

cdef class CyInterpreter:
    """
    Cython-optimized PVM interpreter.
    
    This class provides the same interface as the original Interpreter class
    but with Cython optimizations for the critical execution loop.
    """
    
    # Class-level mapper for instruction dispatch
    cdef object _inst_mapper
    
    def __cinit__(self):
        """Initialize the instruction mapper."""
        self._inst_mapper = CyInstMapper(ALL_CY_TABLES)
    
    @staticmethod
    def execute(
        program: INT_Program,
        program_counter: int,
        gas: int,
        registers: List[int],
        memory,
        logger: Union[Any, None] = None,
    ) -> Tuple[ExecutionStatus, int, int, list, INT_Memory]:
        """
        Execute the program blob as per Psi specification.
        
        This method maintains identical semantics to the original but with
        optimized inner loop performance using Cython.
        """
        # Create instance to use the mapper
        interpreter = CyInterpreter()
        # reg_arr = array.array("Q", registers)
        # cdef uint64_t[:] reg_array = reg_arr  # Typed memoryview for registers
        # cdef uint32_t program_counter_c = <uint32_t>(program_counter)
        # cdef int32_t gas_c = <int32_t>(gas)
        return interpreter._execute_optimized(program, program_counter, gas, registers, memory, logger)
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef tuple _execute_optimized(
        self,
        object program, 
        int program_counter,
        int gas,
        list registers, 
        object memory,  
        object logger,
    ):
        """
        Optimized execution loop with Cython performance improvements.
        
        Key optimizations:
        - Typed local variables for gas accounting and program counter
        - Reduced Python object overhead in tight loop
        - Optimized status checking
        """
        # Use C integers for performance-critical variables
        cdef int64_t remaining_gas = gas
        cdef int32_t pc = program_counter
        cdef int32_t gas_cost
        cdef bint should_break = False
        
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
                result, gas_cost = self._inst_mapper.process_instruction(program, pc, registers, memory)
                status, pc, registers, memory = result
                
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
                registers=registers,
                memory=memory,
            )

        # Convert C integers back to Python for return
        return status, int(pc), int(remaining_gas), registers, memory

