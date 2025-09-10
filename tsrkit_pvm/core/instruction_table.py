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
    def __init__(self, counter: int, program: "Program", skip_index: int):
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

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
