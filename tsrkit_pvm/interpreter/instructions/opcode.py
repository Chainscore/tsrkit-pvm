from dataclasses import dataclass
from typing import Any, Callable, Tuple

from ..memory import Memory
from ..status import ExecutionStatus

OpReturn = Tuple[ExecutionStatus, Any, list, Memory]

@dataclass
class OpCode:
    name: str
    fn: Callable[[Any, list, Memory], OpReturn]
    gas: int
    is_terminating: bool
