from dataclasses import dataclass
from typing import Any, Callable, Tuple

OpReturn = Any


@dataclass
class OpCode:
    name: str
    fn: Callable
    gas: int
    is_terminating: bool
