from bisect import bisect_right
from math import floor
from typing import Any, Dict, Tuple
from tsrkit_pvm.core.program_base import Program
from ..common.constants import PVM_ADDR_ALIGNMENT
from ..common.status import CONTINUE, HALT, PANIC, ExecutionStatus, PvmError
from .instructions.inst_map import BlockInfo, inst_map


class INT_Program(Program):
    """This is the program blob which the PVM will execute."""
    
    def __post_init__(self) -> None:
        super().__post_init__()
        # Initialize instance attributes
        self._skip_cache: list[int] = []
        self._basic_blocks_set: set[int] = set()
        self._exec_blocks: Dict[int, BlockInfo] = {}
        
        # Pre-compute skip values for all positions to eliminate runtime overhead.
        bitmask_len = len(self.offset_bitmask)
        self._skip_cache = [0] * bitmask_len
        
        for i in range(bitmask_len):
            skip_value = bitmask_len
            for j in range(i + 1, bitmask_len + 1):
                if self._extended_bitmask[j]:
                    skip_value = j - i - 1
                    break
            self._skip_cache[i] = min(24, skip_value)
            
        basic_blocks = [0]
        for n in range(len(self.instruction_set)):
            if (
                    self.offset_bitmask[n] and 
                    inst_map.is_terminating(self.instruction_set[n]) and 
                    self.instruction_set[n] < 256 and
                    inst_map._dispatch_table[self.instruction_set[n]] != None
            ):
                next_block = n + 1 + self.skip(n)
                # Check for next block, if its valid start or not.
                if (
                    next_block < len(self.instruction_set)
                    and self.offset_bitmask[next_block]
                    and self.instruction_set[next_block] < 256
                    and inst_map._dispatch_table[self.instruction_set[next_block]] is not None
                ):
                    basic_blocks.append(next_block)
        
        self.basic_blocks = sorted(set(basic_blocks))
        self._basic_blocks_set = set(self.basic_blocks)
        self.jump_table_len = len(self.jump_table)
        

    def skip(self, pc: int) -> int:
        """
        Skip the instructions until the next opcode is found.
        Args:
            pc: Current index
        Returns:
            Distance to the next opcode.
        """
        # Direct list access is faster than dict.get()
        try: 
            return self._skip_cache[pc]
        except IndexError:
            return 0

    def branch(
        self, counter: int, branch: int, condition: bool, validate_fallthrough: bool = False
    ) -> Tuple[ExecutionStatus, int]:
        fallthrough = counter + 1 + self.skip(counter)
        if validate_fallthrough and (
            branch not in self._basic_blocks_set
            or fallthrough not in self._basic_blocks_set
        ):
            raise PvmError(PANIC)
        if not condition:
            return CONTINUE, fallthrough
        elif branch not in self._basic_blocks_set:
            raise PvmError(PANIC)
        return CONTINUE, branch

    def djump(self, counter: int, a: int) -> Tuple[ExecutionStatus, int]:
        if a == 2**32 - 2**16:
            return HALT, counter
        index = floor(a // PVM_ADDR_ALIGNMENT) - 1
        if (
            a == 0
            or index >= self.jump_table_len
            or a % PVM_ADDR_ALIGNMENT != 0
            or self.jump_table[index] not in self._basic_blocks_set
        ):
            raise PvmError(PANIC)
        return CONTINUE, self.jump_table[index]

    def containing_basic_block_start(self, pc: int) -> int:
        index = bisect_right(self.basic_blocks, pc) - 1
        if index < 0:
            return 0
        return self.basic_blocks[index]
