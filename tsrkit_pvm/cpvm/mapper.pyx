# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: profile=True

"""
Cython optimized instruction mapper and dispatch system.
"""

from typing import List, Any, Dict, Tuple, Optional, Union
from libc.stdint cimport int64_t, int32_t, uint8_t, uint32_t, uint64_t
from libc.string cimport memset
from cpython.mem cimport PyMem_Malloc, PyMem_Free

# Simple C struct for gas costs and flags only (no Python objects)
cdef struct COpInfo:
    uint8_t gas_cost
    uint8_t is_terminating

cdef class CyInstructionHandler:
    """Cython optimized instruction handler."""
    cdef public str name
    cdef public object fn
    cdef public int gas_cost
    cdef public bint is_terminating
    cdef public object table_class
    
    def __init__(self, str name, object fn, int gas_cost, bint is_terminating, object table_class):
        self.name = name
        self.fn = fn
        self.gas_cost = gas_cost
        self.is_terminating = is_terminating
        self.table_class = table_class

cdef class CyInstMapper:
    """
    Cython optimized instruction mapper with direct opcode-to-handler dispatch table.
    """
    cdef COpInfo* _op_info_table
    cdef uint64_t _terminating_mask
    cdef dict _basic_blocks
    cdef list _dispatch_table  # 256-entry list of CyInstructionHandler
    cdef list _all_tables

    def __init__(self, all_tables: List[type]):
        self._all_tables = all_tables
        self._basic_blocks = {}
        self._dispatch_table = [None] * 256

        # Allocate C arrays for opcode info only
        self._op_info_table = <COpInfo*>PyMem_Malloc(256 * sizeof(COpInfo))
        if not self._op_info_table:
            raise MemoryError("Failed to allocate opcode info table")
        memset(self._op_info_table, 0, 256 * sizeof(COpInfo))
        self._terminating_mask = 0
        self._build_dispatch_table()
    
    def __dealloc__(self):
        """Clean up allocated memory."""
        if self._op_info_table:
            PyMem_Free(self._op_info_table)
    
    cdef void _build_dispatch_table(self):
        cdef int32_t opcode
        cdef COpInfo* op_info
        for table_class in self._all_tables:
            instruction_table = table_class.table()
            for opcode, op_code in instruction_table.items():
                if 0 <= opcode < 256:
                    op_info = &self._op_info_table[opcode]
                    op_info.gas_cost = op_code.gas
                    op_info.is_terminating = 1 if op_code.is_terminating else 0
                    self._dispatch_table[opcode] = CyInstructionHandler(
                        op_code.name, op_code.fn, op_code.gas, op_code.is_terminating, table_class
                    )
                    if op_code.is_terminating:
                        self._terminating_mask |= (1UL << opcode)
    
    cpdef tuple process_instruction(self, object program, int32_t program_counter, 
                                   list registers, object memory):
        """
        Execute an instruction using the optimized dispatch table.
        """
        cdef object block = self.get_block(program, program_counter)
        return block.execute(program, program_counter, registers, memory)
    
    cpdef int32_t get_gas_cost(self, int32_t opcode):
        """Get gas cost with direct C array lookup."""
        if 0 <= opcode < 256:
            return self._op_info_table[opcode].gas_cost
        return 0
    
    cpdef bint is_terminating(self, int32_t opcode):
        """Check if instruction is terminating with bitwise operation."""
        if 0 <= opcode < 256:
            return bool((self._terminating_mask >> opcode) & 1)
        return False
    
    cpdef object get_block(self, object program, int32_t start_pc):
        """Get compiled block from cache or compile new one."""
        if start_pc in self._basic_blocks:
            return self._basic_blocks[start_pc]
        
        # Compile block and cache it
        block = self._compile_block(program, start_pc)
        self._basic_blocks[start_pc] = block
        return block
    
    cdef object _compile_block(self, object program, int32_t start_pc):
        """Compile a basic block with C-level optimizations."""
        cdef int32_t current_pc = start_pc
        cdef int32_t opcode
        cdef CyInstructionHandler handler
        cdef int32_t total_gas = 0
        cdef int32_t next_block_start = -1
        
        # Find next basic block boundary
        if hasattr(program, 'basic_blocks'):
            for bb_start in sorted(program.basic_blocks):
                if bb_start > start_pc:
                    next_block_start = bb_start
                    break
        
        compiled_instructions = []
        
        while current_pc < len(program.zeta):
            if next_block_start >= 0 and current_pc >= next_block_start:
                break
            opcode = program.zeta[current_pc]
            # print(">> Compiling Opcode:", opcode, "at PC:", current_pc)
            if opcode < 0 or opcode >= 256:
                raise ValueError(f"Invalid opcode: {opcode} at PC {current_pc}")
            handler = self._dispatch_table[opcode]
            if handler is None or handler.fn is None:
                raise ValueError(f"No handler for opcode: {opcode} at PC {current_pc}")
            skip_count = program.skip(current_pc)
            table_instance = handler.table_class(
                counter=current_pc,
                program=program,
                skip_index=skip_count
            )
            args = table_instance.get_props()
            compiled_inst = CyCompiledInstruction(
                opcode=opcode,
                offset=current_pc - start_pc,
                handler=handler,
                args=args,
                table=table_instance,
            )
            compiled_instructions.append(compiled_inst)
            total_gas += handler.gas_cost
            if handler.is_terminating:
                end_pc = current_pc + 1
                break
            current_pc += 1 + skip_count
        else:
            end_pc = current_pc
        return CyBlockInfo(
            end_pc=end_pc,
            total_gas=total_gas,
            instructions=compiled_instructions,
            instruction_count=len(compiled_instructions)
        )

class CyCompiledInstruction:
    """Python wrapper for CCompiledInstruction."""
    def __init__(self, opcode: int, offset: int, handler, args: List[int], table):
        self.opcode = opcode
        self.offset = offset
        self.handler = handler
        self.args = args
        self.table = table

class CyBlockInfo:
    """Python wrapper for CBlockInfo with optimized execution."""
    def __init__(self, end_pc: int, total_gas: int, instructions: List, instruction_count: int):
        self.end_pc = end_pc
        self.total_gas = total_gas
        self.instructions = instructions
        self.instruction_count = instruction_count
    
    def execute(self, program: Any, start_pc: int, registers: List[int], 
                memory: Any) -> Tuple[Tuple[Any, int, List[int], Any], int]:
        """Execute block with optimized loop."""
        cdef int32_t current_pc = start_pc
        cdef int32_t i
        cdef object status = None
        cdef int32_t next_pc
        
        current_registers = registers
        current_memory = memory
        
        # Tight execution loop
        for i in range(len(self.instructions)):
            compiled_inst = self.instructions[i]

            # Execute instruction
            result = compiled_inst.handler.fn(
                compiled_inst.table, current_registers, current_memory, *compiled_inst.args
            )
            
            # Unpack result
            status, next_pc, current_registers, current_memory = result
            
            # Check for termination
            if compiled_inst.handler.is_terminating:
                return (status, next_pc, current_registers, current_memory), self.total_gas
            
            # Check for non-continue status
            if status != 0:  # Assuming CONTINUE = 0
                return (status, next_pc, current_registers, current_memory), i + 1
            
            current_pc = next_pc
        
        # Block completed normally
        return (status, current_pc, current_registers, current_memory), self.total_gas
