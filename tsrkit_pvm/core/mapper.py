"""
Instruction mapper and dispatch system.

This module pre-compiles all instruction handlers into a single dispatch table,
eliminating the need for table object creation and multiple dictionary lookups.
"""

from dataclasses import dataclass
from http.client import CONTINUE
from typing import Callable, List, Optional, Tuple, Any, Dict, Type, Union

from tsrkit_pvm.core.instruction_table import InstructionTable
from tsrkit_pvm.common.status import ExecutionStatus, PvmError, PANIC
from tsrkit_pvm.core.opcode import OpCode


@dataclass
class InstructionHandler:
    """Instruction handler data."""

    name: str
    fn: Callable
    gas_cost: int
    is_terminating: bool
    table_class: type  # For creating table instances when needed

@dataclass
class CompiledInstruction:
    """Pre-compiled instruction with decoded operands."""
    handler: InstructionHandler # Handler for this instruction
    args: List[int]  # Pre-decoded instruction arguments
    table: type[InstructionTable] # Table instance for this instruction

@dataclass
class BlockInfo:
    """Compiled basic block with pre-decoded instructions."""
    total_gas: int         # Total gas cost for entire block
    instructions: List[CompiledInstruction]  # Pre-compiled instructions
    
    def execute(self, program: Any, start_pc: int, registers: List[int], memory: Any) -> Tuple[Tuple[Any, int, List[int], Any], int]:
        """Execute this block starting from start_pc with given registers and memory."""
        current_pc = start_pc
        current_registers = registers
        current_memory = memory
        status = None
        
        for i, compiled_inst in enumerate(self.instructions):
            # Execute the instruction with pre-decoded arguments
            result = compiled_inst.handler.fn(
                compiled_inst.table, current_registers, current_memory, *compiled_inst.args
            )
            
            # Unpack result (status, pc, registers, memory)
            status, next_pc, current_registers, current_memory = result
            
            # If instruction terminates execution, return immediately
            if compiled_inst.handler.is_terminating:
                return (status, next_pc, current_registers, current_memory), self.total_gas
            
            if status != CONTINUE:
                return (status, next_pc, current_registers, current_memory), i + 1
            
            # For non-terminating instructions, advance PC normally
            # The instruction handler should have set the correct next PC
            current_pc = next_pc
                
        # Block completed normally (shouldn't happen as blocks end with terminating instructions)
        return (status, current_pc, current_registers, current_memory), self.total_gas

class InstMapper:
    """
    Instruction table map that pre-compiles all instruction handlers
    into a single dispatch table for efficient performance.
    """

    _dispatch_table: List[Union[InstructionHandler, None]] = [None] * 256
    _gas_costs: bytes = b""
    _terminating_mask: int = 0
    
    _exec_blocks: Dict[int, BlockInfo] = {}

    def __init__(self, all_tables: List[type[InstructionTable]]):
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
        self, program: Any, program_counter: int, registers: List[int], memory: Any
    ) -> Tuple[Tuple[Any, int, List[int], Any], int]:
        """
        Execute an instruction directly using the optimized dispatch table.

        This version completely eliminates table instance creation by using
        cached instances that are reused and updated in-place.
        """
        
        # ---- Block based execution ---- #
        block = self.get_block(program, program_counter)
        return block.execute(program, program_counter, registers, memory)
        
        # ---- Unoptimized, but better if caching is program isolayted for some reason ---- #
        # handler = self._dispatch_table[program.zeta[program_counter]]
        # if handler is None:
        #     raise ValueError("Recompiler: Invalid opcode")
        # table_instance = handler.table_class(counter=program_counter, program=program, skip_index=program.skip(program_counter))
        # props = table_instance.get_props()
        # result = handler.fn(table_instance, registers, memory, *props)
        # return result, handler.gas_cost

    def get_gas_cost(self, opcode: int) -> int:
        """Get gas cost for an opcode with direct lookup - no dictionary access."""
        return self._gas_costs[opcode]

    def is_terminating(self, opcode: int) -> bool:
        """Check if an opcode is terminating with direct lookup."""
        return bool((self._terminating_mask >> opcode) & 1)

    def get_block(self, program: Any, start_pc: int) -> BlockInfo:
        """Get a compiled block from cache or compile it if not cached."""
        if start_pc in self._exec_blocks:
            cached_block: BlockInfo = self._exec_blocks[start_pc]
            return cached_block
        
        # Compile the block and cache it
        block = self._compile_block(program, start_pc)
        self._exec_blocks[start_pc] = block
        return block

    def _compile_block(self, program: Any, start_pc: int) -> BlockInfo:
        """Compile a basic block starting at the given PC."""
        # print("Compiling block at PC:", start_pc)
        compiled_instructions = []
        current_pc = start_pc
        total_gas = 0

        while current_pc < len(program.zeta):
            opcode = program.zeta[current_pc]
            handler = self._dispatch_table[opcode]
            
            if handler is None:
                raise ValueError(f"Invalid opcode: {opcode} at PC {current_pc}")
            
            # Create temporary table instance to get instruction arguments
            skip_count = program.skip(current_pc)
            table_instance = handler.table_class(counter=current_pc, program=program, skip_index=skip_count)
            args = table_instance.get_props()
            
            # Create compiled instruction
            compiled_inst = CompiledInstruction(
                # opcode=opcode,
                # offset=current_pc - start_pc,
                handler=handler,
                args=args,
                table=table_instance,
            )
            
            compiled_instructions.append(compiled_inst)
            total_gas += handler.gas_cost
            
            # Stop at terminating instructions
            if handler.is_terminating:
                # For terminating instructions, the end_pc should be current_pc + 1
                break
                
            # Move to next instruction
            current_pc += 1 + skip_count
        
        return BlockInfo(
            total_gas=total_gas,
            instructions=compiled_instructions,
        )

    def execute_block(self, block: BlockInfo, program: Any, initial_pc: int, 
                     registers: List[int], memory: Any) -> Tuple[Tuple[Any, int, List[int], Any], int]:
        """Execute a compiled block in a tight loop."""
        current_pc = initial_pc
        current_registers = registers
        current_memory = memory
        status = None
        
        # Process all instructions in the block
        for i, compiled_inst in enumerate(block.instructions):
            # Create table instance for this instruction with the current PC
            table_instance = compiled_inst.handler.table_class(
                counter=current_pc, program=program
            )
            
            # Execute the instruction with pre-decoded arguments
            result = compiled_inst.handler.fn(
                table_instance, current_registers, current_memory, *compiled_inst.args
            )
            
            # Unpack result (status, pc, registers, memory)
            status, next_pc, current_registers, current_memory = result
            
            # If instruction terminates execution, return immediately
            if compiled_inst.handler.is_terminating:
                return (status, next_pc, current_registers, current_memory), block.total_gas
            
            # For non-terminating instructions, advance PC normally
            # The instruction handler should have set the correct next PC
            current_pc = next_pc
                
        # Block completed normally (shouldn't happen as blocks end with terminating instructions)
        return (status, current_pc, current_registers, current_memory), block.total_gas
