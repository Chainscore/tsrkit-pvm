"""Abstract base class for PVM implementations."""

from abc import ABC, abstractmethod
from typing import Tuple, Any, Optional, TYPE_CHECKING

from ..common.status import ExecutionStatus

from .program_base import Program
from .memory import Memory


class PVM(ABC):
    """Abstract base class for PVM implementations."""

    ...
