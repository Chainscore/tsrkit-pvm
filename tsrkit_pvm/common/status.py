from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


@dataclass
class ExecValue:
    name: str
    code: int
    register: Optional[int]


class ExecutionStatus(Enum):
    HALT = ExecValue("halt", 0, None)
    PANIC = ExecValue("panic", 1, None)
    PAGE_FAULT = ExecValue("page-fault", 2, None)
    HOST = ExecValue("host", 3, None)
    OUT_OF_GAS = ExecValue("out-of-gas", 4, None)
    CONTINUE = ExecValue("continue", 5, None)


class HostStatus(Enum):
    NONE = 2**64 - 1
    WHAT = 2**64 - 2
    OOB = 2**64 - 3
    WHO = 2**64 - 4
    FULL = 2**64 - 5
    CORE = 2**64 - 6
    CASH = 2**64 - 7
    LOW = 2**64 - 8
    HUH = 2**64 - 9
    OK = 0


# Constructured statuses to use directly
# Panic
PANIC: ExecutionStatus = ExecutionStatus(ExecutionStatus.PANIC)


# Page fault with a register value
def PAGE_FAULT(register: int) -> ExecutionStatus:
    result: Any = ExecutionStatus.PAGE_FAULT
    result.value.register = register
    return ExecutionStatus(result)


# Halt
HALT: ExecutionStatus = ExecutionStatus(ExecutionStatus.HALT)

# Host call with a register value
def HOST(register: int) -> ExecutionStatus:
    result: Any = ExecutionStatus.HOST
    result.value.register = register
    return ExecutionStatus(result)

# Out of gas
OUT_OF_GAS: ExecutionStatus = ExecutionStatus(ExecutionStatus.OUT_OF_GAS)
# Continue
CONTINUE: ExecutionStatus = ExecutionStatus(ExecutionStatus.CONTINUE)

class PvmError(Exception):
    def __init__(self, code: ExecutionStatus, message: str = "") -> None:
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code.name}: {self.message}"
