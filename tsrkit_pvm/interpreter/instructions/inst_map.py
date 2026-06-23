"""
Instruction mapper and dispatch system.

This module pre-compiles all instruction handlers into a single dispatch table,
eliminating the need for table object creation and multiple dictionary lookups.
"""

from .tables.i_imm import InstructionsWArgs1Imm
from .tables.i_offset import WArgsOneOffset
from .tables.i_reg_i_ewimm import InstructionsWArgs1Imm1EwImm
from .tables.i_reg_i_imm import InstructionsWArgs1Reg1Imm
from .tables.i_reg_i_imm_i_offset import InstructionsWArgs1Reg1Imm1Offset
from .tables.i_reg_ii_imm import InstructionsWArgs1Reg2Imm
from .tables.ii_imm import InstructionsWArgs2Imm
from .tables.ii_reg import InstructionsWArgs2Reg
from .tables.ii_reg_i_imm import InstructionsWArgs2Reg1Imm
from .tables.ii_reg_i_offset import InstructionsWArgs2Reg1Offset
from .tables.ii_reg_ii_imm import InstructionsWArgs2Reg2Imm
from .tables.iii_reg import InstructionsWArgs3Reg
from .tables.wo_args import InstructionsWoArgs

from typing import Callable, List, Optional, Tuple, Any, Dict, Type, Union

from tsrkit_pvm.core.instruction_table import InstructionTable
from tsrkit_pvm.common.status import CONTINUE, ExecutionStatus, PvmError, PANIC
from tsrkit_pvm.core.opcode import OpCode
from tsrkit_pvm.gas.props import resolve_gas_profile
from tsrkit_pvm.gas.simulator import compute_basic_block_gas

all_tables = [
    InstructionsWoArgs,
    InstructionsWArgs1Imm,
    InstructionsWArgs1Imm1EwImm,
    InstructionsWArgs2Imm,
    WArgsOneOffset,
    InstructionsWArgs1Reg1Imm,
    InstructionsWArgs1Reg2Imm,
    InstructionsWArgs1Reg1Imm1Offset,
    InstructionsWArgs2Reg,
    InstructionsWArgs2Reg1Imm,
    InstructionsWArgs2Reg1Offset,
    InstructionsWArgs2Reg2Imm,
    InstructionsWArgs3Reg,
]

class InstructionHandler:
    """Instruction handler data."""
    __slots__ = ('op_data', 'table_class')
    
    def __init__(self, op_data: OpCode, table_class: type):
        self.op_data = op_data
        self.table_class = table_class

class CompiledInstruction:
    """Pre-compiled instruction with decoded operands and cached function pointers."""
    __slots__ = ('pc', 'opcode', 'handler', 'args', 'table', 'fn', 'is_terminating')
    
    def __init__(self, pc: int, opcode: int, handler: InstructionHandler, args: List[int], table: type[InstructionTable], fn: Callable, is_terminating: bool):
        self.pc = pc
        self.opcode = opcode
        self.handler = handler
        self.args = args
        self.table = table
        self.fn = fn
        self.is_terminating = is_terminating

class BlockInfo:
    """Compiled basic block with pre-decoded instructions."""
    __slots__ = ('start_pc', 'total_gas', 'instructions', 'index_by_pc')
    
    def __init__(self, start_pc: int, total_gas: int, instructions: List[CompiledInstruction]):
        self.start_pc = start_pc
        self.total_gas = total_gas
        self.instructions = instructions
        self.index_by_pc = {instruction.pc: index for index, instruction in enumerate(instructions)}
    
    def execute(self, program: Any, start_pc: int, registers: List[int], memory: Any) -> Tuple[Tuple[Any, int, List[int], Any], bool]:
        """Execute this block starting from start_pc with given registers and memory.
        
        Ultra-optimized version that uses pre-cached function pointers and flags
        to eliminate all attribute access in the hot execution loop.
        """
        status = None
        
        # Pre-cache data to eliminate repeated attribute access
        instructions = self.instructions
        start_index = self.index_by_pc[start_pc]
        
        for compiled_inst in instructions[start_index:]:
            # All critical data is now pre-cached in CompiledInstruction
            try:
                status, next_pc, registers, memory = compiled_inst.fn(
                    compiled_inst.table, registers, memory, *compiled_inst.args
                )
            except PvmError as error:
                error.instruction_counter = compiled_inst.pc
                error.executed_terminator = compiled_inst.is_terminating
                raise

            # Use pre-cached termination flag
            if compiled_inst.is_terminating:
                return (status, next_pc, registers, memory), True
                
            if status != CONTINUE:
                return (status, next_pc, registers, memory), False
                
        # Block completed normally (shouldn't happen as blocks end with terminating instructions)
        return (status, start_pc, registers, memory), False

class InstMapper:
    """
    Instruction table map that pre-compiles all instruction handlers
    into a single dispatch table for efficient performance.
    """

    _dispatch_table: List[Union[InstructionHandler, None]] = [None] * 256

    def __init__(self):
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
        self, program: Any, program_counter: int, registers: List[int], memory: Any
    ) -> Tuple[Tuple[Any, int, List[int], Any], int]:
        """
        Execute an instruction directly using the optimized dispatch table.

        This version completely eliminates table instance creation by using
        cached instances that are reused and updated in-place.
        """
        
        # ---- Block based execution ---- #
        block = self.get_block(program, program.containing_basic_block_start(program_counter))
        return block.execute(program, program_counter, registers, memory)
        
        # ---- Unoptimized, but better if caching is program isolayted for some reason ---- #
        # handler = self._dispatch_table[program.zeta[program_counter]]
        # if handler is None:
        #     raise ValueError("Recompiler: Invalid opcode")
        # table_instance = handler.table_class(counter=program_counter, program=program, skip_index=program.skip(program_counter))
        # props = table_instance.get_props()
        # result = handler.op_data.fn(table_instance, registers, memory, *props)
        # return result

    def is_terminating(self, opcode: int) -> bool:
        """Check if an opcode is terminating with direct lookup."""
        opc = self._dispatch_table[opcode]
        if opc is None:
            return True
        return opc.op_data.is_terminating

    def get_block(self, program: Any, start_pc: int) -> BlockInfo:
        """Get a compiled block from cache or compile it if not cached."""
        try:
            block = program._exec_blocks[start_pc]
        except KeyError:
            block = self._compile_block(program, start_pc)
            program._exec_blocks[start_pc] = block
        return block

    def _compile_block(self, program: Any, start_pc: int) -> BlockInfo:
        """Compile a basic block starting at the given PC with aggressive pre-caching."""
        compiled_instructions = []
        gas_instructions = []
        current_pc = start_pc

        while True:
            opcode = program.zeta[current_pc]
            handler = self._dispatch_table[opcode]
            
            if handler is None:
                raise ValueError(f"Invalid opcode: {opcode} at PC {current_pc}")
            
            # Create temporary table instance to get instruction arguments
            skip_count = program.skip(current_pc)
            table_instance = handler.table_class(counter=current_pc, program=program, skip_index=skip_count)
            args = table_instance.get_props()
            
            # Pre-cache all critical data to eliminate attribute access in execution
            op_data = handler.op_data
            fn = op_data.fn
            is_terminating = op_data.is_terminating
            gas_instructions.append(
                resolve_gas_profile(
                    program=program,
                    pc=current_pc,
                    opcode=opcode,
                    args=args,
                    profile=op_data.gas_profile,
                )
            )
            
            # Create compiled instruction with pre-cached function and flags
            compiled_inst = CompiledInstruction(
                pc=current_pc,
                opcode=opcode,
                handler=handler,
                args=args,
                table=table_instance,
                fn=fn,  # Pre-cached function pointer
                is_terminating=is_terminating,  # Pre-cached termination flag
            )
            
            compiled_instructions.append(compiled_inst)
            
            # Stop at terminating instructions
            if is_terminating:
                break
                
            # Move to next instruction
            current_pc += 1 + skip_count
        
        return BlockInfo(
            start_pc=start_pc,
            total_gas=compute_basic_block_gas(gas_instructions),
            instructions=compiled_instructions,
        )

inst_map = InstMapper()
