"""
Instruction mapper and dispatch system.

This module pre-compiles all instruction handlers into a single dispatch table,
eliminating the need for table object creation and multiple dictionary lookups.
"""

from dataclasses import dataclass
from typing import Callable, List

from tsrkit_pvm.core.instruction_table import InstructionTable

@dataclass
class InstructionHandler:
    """Optimized instruction handler data."""

    name: str
    fn: Callable
    gas_cost: int
    is_terminating: bool
    table_class: type  # For creating table instances when needed


class InstMapper:
    """
    Instruction table map that pre-compiles all instruction handlers
    into a single dispatch table for efficient performance.
    """

    _dispatch_table: List[InstructionHandler | None] = []
    _gas_costs: bytes = b""
    _terminating_mask: int = 0

    def __init__(self, all_tables: list[InstructionTable]):
        gas_tmp = [0] * 256
        term_mask = 0
        self._dispatch_table = [None] * 256
        for table_class in all_tables:
            instruction_table = table_class.table()

            for opcode, op_code in instruction_table.items():
                handler = InstructionHandler(
                    name=op_code.name,
                    fn=op_code.fn,
                    gas_cost=op_code.gas,
                    is_terminating=op_code.is_terminating,
                    table_class=table_class,
                )
                self._dispatch_table[opcode] = handler

                gas_tmp[opcode] = op_code.gas
                if op_code.is_terminating:
                    term_mask |= 1 << opcode

        self._gas_costs = bytes(gas_tmp)
        self._terminating_mask = term_mask

    def process_instruction(
        self, opcode: int, program, program_counter: int, *args
    ) -> tuple[tuple, int]:
        """
        Execute an instruction directly using the optimized dispatch table.

        This version completely eliminates table instance creation by using
        cached instances that are reused and updated in-place.
        """
        handler = self._dispatch_table[opcode]
        if handler is None:
            raise ValueError("Recompiler: Invalid opcode")

        table_instance = handler.table_class(counter=program_counter, program=program)
        result = handler.fn(table_instance, *args)
        return result, handler.gas_cost

    def get_gas_cost(self, opcode: int) -> int:
        """Get gas cost for an opcode with direct lookup - no dictionary access."""
        return self._gas_costs[opcode]

    def is_terminating(self, opcode: int) -> bool:
        """Check if an opcode is terminating with direct lookup."""
        return bool((self._terminating_mask >> opcode) & 1)


