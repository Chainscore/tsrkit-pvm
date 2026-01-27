"""
Instruction mapper and dispatch system.

This module pre-compiles all instruction handlers into a single dispatch table,
eliminating the need for table object creation and multiple dictionary lookups.
"""

from .tables.i_offset import WArgsOneOffset
from .tables.i_reg_i_ewimm import InstructionsWArgs1Imm1EwImm
from .tables.i_reg_i_imm import InstructionsWArgs1Reg1Imm
from .tables.i_reg_i_imm_i_offset import InstructionsWArgs1Reg1Imm1Offset
from .tables.ii_reg_i_imm import InstructionsWArgs2Reg1Imm
from .tables.ii_reg_i_offset import InstructionsWArgs2Reg1Offset
from .tables.ii_imm import InstructionsWArgs2Imm
from .tables.wo_args import InstructionsWoArgs
from .tables.i_imm import InstructionsWArgs1Imm
from .tables.i_reg_ii_imm import InstructionsWArgs1Reg2Imm
from .tables.ii_reg import InstructionsWArgs2Reg
from .tables.ii_reg_ii_imm import InstructionsWArgs2Reg2Imm
from .tables.iii_reg import InstructionsWArgs3Reg
from dataclasses import dataclass
from typing import Callable, List
from tsrkit_pvm.core.instruction_table import InstructionTable
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple, Any, Dict, Type, Union
from tsrkit_pvm.core.instruction_table import InstructionTable
from tsrkit_pvm.common.status import ExecutionStatus, PvmError, PANIC
from tsrkit_pvm.core.opcode import OpCode


@dataclass
class InstructionHandler:
    """Instruction handler data."""
    op_data: OpCode
    table_class: type

class InstMapper:
    """
    Instruction table map that pre-compiles all instruction handlers
    into a single dispatch table for efficient performance.
    """

    _dispatch_table: List[Union[InstructionHandler, None]] = [None] * 256

    def __init__(self, all_tables: List[type[InstructionTable]]):
        self._dispatch_table = [None] * 256
        
        for table_class in all_tables:
            instruction_table = table_class.table()

            for opcode, op_code in instruction_table.items():
                handler = InstructionHandler(
                    op_data=op_code,
                    table_class=table_class,
                )
                self._dispatch_table[opcode] = handler


    def process_instruction(
        self, program: Any, program_counter: int, *args: Any
    ) -> Tuple[None, int]:
        """
        Execute an instruction directly using the optimized dispatch table.

        This version completely eliminates table instance creation by using
        cached instances that are reused and updated in-place.
        """
        handler = self._dispatch_table[program.zeta[program_counter]]
        if handler is None:
            raise ValueError("Recompiler: Invalid opcode")
        table_instance = handler.table_class(
            counter=program_counter, 
            program=program, 
            skip_index=program.skip(program_counter)
        )
        props = table_instance.get_props()
        result = handler.op_data.fn(table_instance, *args, *props)

        return result, handler.op_data.gas

    def get_gas_cost(self, opcode: int) -> int:
        """Get gas cost for an opcode with direct lookup - no dictionary access."""
        opc = self._dispatch_table[opcode]
        if opc is None:
            raise PvmError(PANIC, f"Invalid opcode: {opcode}")
        return opc.op_data.gas

    def is_terminating(self, opcode: int) -> bool:
        """Check if an opcode is terminating with direct lookup."""
        opc = self._dispatch_table[opcode]
        if opc is None:
            return True
        return opc.op_data.is_terminating


inst_map = InstMapper(
    [
        InstructionsWoArgs,
        InstructionsWArgs1Imm1EwImm,
        WArgsOneOffset,
        InstructionsWArgs1Reg1Imm,
        InstructionsWArgs1Reg1Imm1Offset,
        InstructionsWArgs2Imm,
        InstructionsWArgs2Reg1Imm,
        InstructionsWArgs2Reg1Offset,
        InstructionsWArgs1Imm,
        InstructionsWArgs1Reg2Imm,
        InstructionsWArgs2Reg,
        InstructionsWArgs2Reg2Imm,
        InstructionsWArgs3Reg,
    ]
)
