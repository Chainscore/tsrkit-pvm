from dataclasses import dataclass
from logging import Logger
from typing import Any, List, Tuple, Union
from tsrkit_pvm.core.ipvm import PVM
from .instructions.inst_map import inst_map
from .memory import INT_Memory
from .program import INT_Program
from ..common.status import OUT_OF_GAS, PAGE_FAULT, PANIC, ExecutionStatus, PvmError


class Interpreter(PVM):
    """Interpreter mode of PVM"""

    @classmethod
    def execute(
        cls,
        program: INT_Program,
        program_counter: int,
        gas: int,
        registers: List[int],
        memory: INT_Memory,
        logger: Union[Any, None] = None,
    ) -> Tuple[ExecutionStatus, int, int, list, INT_Memory]:
        """
        Execute the program blob `p` as per Psi specification.

        Args:
            program: Program context / Cached for faster execution
            program_counter: Initial program counter
            gas: Gas provided for execution
            registers: Initial registers
            memory: Initial memory

        Returns:
            ExecutionStatus: Status of the execution - Either PANIC, HALT, PAGE-FAULT, HOST, OUT-OF-GAS, or CONTINUE
            U32: Final program counter
            RemainingGas: Remaining gas
            Registers: Final registers
            Memory: Final memory
        """
        remaining_gas = gas

        if logger:
            logger.debug(
                "Starting PVM execution",
                registers=registers,
                inst_size=len(program.instruction_set),
                initial_pc=program_counter,
                initial_gas=gas,
                program_size=len(program.zeta),
            )

        while True:
            try:
                (status, program_counter, registers, memory), gas_cost = (
                    inst_map.process_instruction(
                        program, program_counter, registers, memory
                    )
                )
                remaining_gas -= gas_cost

                if remaining_gas < 0:
                    if logger:
                        logger.warning(
                            "PVM - OUT_OF_GAS",
                            final_pc=program_counter,
                            gas_deficit=abs(remaining_gas),
                        )
                    status = OUT_OF_GAS
                    break

                if status == ExecutionStatus.HALT:
                    if logger:
                        logger.info(
                            "PVM - HALT",
                            final_pc=program_counter,
                            gas_remaining=remaining_gas,
                        )
                    break
                elif status == ExecutionStatus.HOST:
                    if logger:
                        logger.debug(
                            "PVM - HOST",
                            pc=program_counter,
                            gas_remaining=remaining_gas,
                        )
                    break

            except PvmError as e:
                if logger:
                    logger.error(
                        "PVM execution error",
                        error_message=str(e),
                        error_code=e.code,
                        pc=program_counter,
                        gas_remaining=remaining_gas,
                    )
                if e.code == PANIC:
                    status = PANIC
                    break
                elif e.code == ExecutionStatus.PAGE_FAULT:
                    status = PAGE_FAULT(e.code.value.register)
                    break
                else:
                    raise e
            except Exception as e:
                if logger:
                    logger.critical(
                        "Unexpected PVM execution error",
                        error=str(e),
                        error_type=type(e).__name__,
                        pc=program_counter,
                    )
                raise e

        if logger:
            logger.info(
                "PVM result",
                final_pc=program_counter,
                gas_remaining=remaining_gas,
                registers=registers,
                memory=memory,
            )

        return status, program_counter, remaining_gas, registers, memory
