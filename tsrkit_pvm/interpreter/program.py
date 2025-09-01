from math import floor
from typing import Dict, Tuple
from tsrkit_pvm.core.program_base import Program
from ..common.constants import PVM_ADDR_ALIGNMENT
from ..common.status import CONTINUE, HALT, PANIC, ExecutionStatus, PvmError
from .instructions.inst_map import inst_map


class INT_Program(Program):
    """This is the program blob which the PVM will execute."""

    _skip_cache: Dict[int, int]
    _basic_blocks_set: set[int]

    def __post_init__(self):
        super().__post_init__()
        self._skip_cache: Dict[int, int] = {}
        self._precompute_skip_values()
        basic_blocks = [0]
        for n in range(len(self.instruction_set)):
            if (
                    self.offset_bitmask[n] and 
                    inst_map.is_terminating(self.instruction_set[n]) and 
                    self.instruction_set[n] < 256 and
                    inst_map._dispatch_table[self.instruction_set[n]] != None
            ):
                basic_blocks.append(n + 1 + self.skip(n))
        
        self.basic_blocks = basic_blocks
        self._basic_blocks_set = set(self.basic_blocks)

    def _precompute_skip_values(self):
        """Pre-compute skip values for all positions to eliminate runtime overhead."""
        for i in range(len(self.offset_bitmask)):
            skip_value = len(self.offset_bitmask)
            for j in range(i + 1, len(self.offset_bitmask) + 1):
                if self._extended_bitmask[j]:
                    skip_value = j - i - 1
                    break

            self._skip_cache[i] = min(24, skip_value)

    def skip(self, pc) -> int:
        """
        Skip the instructions until the next opcode is found.
        Args:
            pc: Current index
        Returns:
            Distance to the next opcode.
        """
        return self._skip_cache.get(pc, 0)

    def branch(
        self, counter: int, branch: int, condition: bool
    ) -> Tuple[ExecutionStatus, int]:
        if not condition:
            return CONTINUE, counter
        elif branch not in self._basic_blocks_set:
            raise PvmError(PANIC)
        return CONTINUE, branch

    def djump(self, counter: int, a: int) -> Tuple[ExecutionStatus, int]:
        if a == 2**32 - 2**16:
            return HALT, counter
        index = floor(a // PVM_ADDR_ALIGNMENT) - 1
        if (
            a == 0
            or index > len(self.jump_table)
            or a % PVM_ADDR_ALIGNMENT != 0
            or self.jump_table[index] not in self._basic_blocks_set
        ):
            raise PvmError(PANIC)
        return CONTINUE, self.jump_table[index]
