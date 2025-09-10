from abc import abstractmethod
from typing import TYPE_CHECKING, Dict, List, Protocol, Tuple, Any
from .opcode import OpCode

if TYPE_CHECKING:
    from tsrkit_pvm.interpreter.program import INT_Program


class InstructionTable(Protocol):
    """
    A protocol for instruction tables.
    Defines a context for executing an instruction from an instruction table
    """

    counter: int
    program: "INT_Program" 
    skip_index: int

    def __init__(self, counter: int, program: "INT_Program", skip_index: int) -> None:
        ...

    @classmethod
    def table(cls) -> Dict[int, OpCode]: 
        ...

    def get_props(self) -> List[int]:
        ...
