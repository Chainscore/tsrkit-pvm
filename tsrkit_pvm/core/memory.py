"""Abstract base class for Memory implementations."""

from abc import ABC, abstractmethod
from typing import List, Sequence, Union


class Memory(ABC):
    """Abstract base class for Memory implementations."""

    @classmethod
    @abstractmethod
    def from_pc(
        cls, read: bytes, write: bytes, args: bytes, z: int, s: int
    ) -> "Memory":
        """Create memory from PVM initialization data."""
        pass

    @abstractmethod
    def alter_accessibility(
        self, start_address: int, length: int, access_type: str
    ) -> None:
        """Alter memory accessibility."""
        pass
