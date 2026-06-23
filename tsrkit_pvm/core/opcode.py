from dataclasses import dataclass, field
from typing import Any, Callable

OpReturn = Any


@dataclass(frozen=True, slots=True)
class ExecutionUnits:
    """GP A.9 execution-unit tuple E = (A, L, S, M, D)."""
    alu: int = 0
    load: int = 0
    store: int = 0
    multiply: int = 0
    divide: int = 0


@dataclass(frozen=True, slots=True)
class GasProfile:
    """GP A.10 gas profile before dynamic costs are resolved."""
    execution_cycles: int | str = 1
    decode_slots: int | tuple = 1
    units: ExecutionUnits = field(default_factory=lambda: ExecutionUnits(1, 0, 0, 0, 0))


@dataclass
class OpCode:
    name:           str
    fn:             Callable
    is_terminating: bool
    gas_profile:    GasProfile = field(default_factory=GasProfile)
