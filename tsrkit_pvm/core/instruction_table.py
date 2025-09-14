from abc import abstractmethod
from typing import TYPE_CHECKING, Dict, List, Protocol, Tuple, Any
from .opcode import OpCode
from .program_base import Program


class InstructionTable(Protocol):
    """
    A protocol for instruction tables.
    Defines a context for executing an instruction from an instruction table
    """

    counter: int
    program: Program
    skip_index: int

    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        ...

    @classmethod
    def table(cls) -> Dict[int, OpCode]: 
        ...

    def get_props(self) -> Any:
        ...
