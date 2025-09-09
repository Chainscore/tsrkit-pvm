from typing import TYPE_CHECKING, Dict, Protocol, Tuple
from tsrkit_pvm.core.program_base import Program
from .opcode import OpCode


class InstructionTable(Protocol):
    """
    A protocol for instruction tables.
    Defines a context for executing an instruction from an instruction table
    """

    counter: int
    program: "Program"

    # Constructor
    def __init__(self, counter: int, program: "Program"):
        self.counter = counter
        self.program = program
        # Inline skip calculation for maximum performance
        if hasattr(program, '_skip_cache') and counter < len(program._skip_cache):
            self.skip_index = program._skip_cache[counter]
        else:
            self.skip_index = 0

    @classmethod
    def table(cls) -> Dict[int, OpCode]: ...

    # Execute the instruction
    def execute(self, opcode: int, *args):
        # Read the opcode from instruction table
        op = self.table()[opcode]
        # Raise an error if the opcode is not found
        if op is None:
            raise ValueError(f"Invalid opcode: {self.program.zeta[self.counter]}")
        # Execute the instruction
        return op.fn(self, *args)
