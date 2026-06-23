from dataclasses import dataclass, field
from typing import Any
from tsrkit_types import (
    U32,
    U8,
    U64,
    Bool,
    Bytes,
    String,
    TypedArray,
    TypedVector,
    structure,
)

from tsrkit_pvm.interpreter.memory import INT_Memory
from tsrkit_pvm.cpvm.cy_memory import CyMemory
from tsrkit_pvm.common.types import Accessibility
Gas = U64
Register = U64


@structure
class Page:
    address: U32
    length: U32
    is_writable: Bool = field(metadata={"name": "is-writable"})


class Registers(TypedArray[Register, 13]): ...


class PageMap(TypedVector[Page]): ...


@structure
class MemoryData:
    address: U32
    contents: TypedVector[U8]


class MemoryChunk(TypedVector[MemoryData]):
    def to_memory(self, page_map: PageMap) -> INT_Memory:
        memory_data = {}
        allowed_read_pages = []
        allowed_write_pages = []
        for memory_entry in self:
            for i, byte in enumerate(memory_entry.contents):
                memory_data[int(memory_entry.address + i)] = int(byte)
        for page in page_map:
            pages = range(int(page.address) // 2**12, (int(page.address) + int(page.length) + 2**12 - 1) // 2**12)
            if page.is_writable:
                allowed_write_pages.extend(pages)
                allowed_read_pages.extend(pages)
            else:
                allowed_read_pages.extend(pages)

        memory = INT_Memory(memory_data, allowed_read_pages, allowed_write_pages)
        return memory
    
    def to_cymemory(self, page_map: PageMap) -> CyMemory:
        memory_data = {}
        allowed_read_pages = []
        allowed_write_pages = []
        for memory_entry in self:
            for i, byte in enumerate(memory_entry.contents):
                memory_data[int(memory_entry.address + i)] = int(byte)
        for page in page_map:
            pages = range(int(page.address) // 2**12, (int(page.address) + int(page.length) + 2**12 - 1) // 2**12)
            if page.is_writable:
                allowed_write_pages.extend(pages)
                allowed_read_pages.extend(pages)
            else:
                allowed_read_pages.extend(pages)

        memory = CyMemory(memory_data, allowed_read_pages, allowed_write_pages)
        return memory


@structure
class PvmTestcase:
    name: String
    initial_regs: Registers = field(metadata={"name": "initial-regs"})
    initial_pc: U32 = field(metadata={"name": "initial-pc"})
    initial_page_map: PageMap = field(metadata={"name": "initial-page-map"})
    initial_memory: MemoryChunk = field(metadata={"name": "initial-memory"})
    initial_gas: Gas = field(metadata={"name": "initial-gas"})
    program: TypedVector[U8]
    expected_status: String = field(metadata={"name": "expected-status"})
    expected_regs: Registers = field(metadata={"name": "expected-regs"})
    expected_pc: U32 = field(metadata={"name": "expected-pc"})
    expected_memory: MemoryChunk = field(metadata={"name": "expected-memory"})
    expected_gas: Gas = field(metadata={"name": "expected-gas"})


@dataclass(frozen=True)
class PvmMemorySegment:
    address: int
    contents: list[int]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PvmMemorySegment":
        return cls(address=int(data["address"]), contents=[int(x) for x in data["contents"]])

    def write_unchecked(self, memory: INT_Memory) -> None:
        """Load vector-provided bytes without applying PVM write permissions."""
        address = self.address & (2**32 - 1)
        remaining = bytes(self.contents)
        offset = 0
        while offset < len(remaining):
            cursor = address + offset
            page = memory._page_for(cursor, create=True)
            page_offset = cursor & (2**12 - 1)
            chunk_len = min(2**12 - page_offset, len(remaining) - offset)
            page[page_offset : page_offset + chunk_len] = remaining[offset : offset + chunk_len]
            offset += chunk_len
        memory._hot_page_num = -1
        memory._hot_page_data = None
        memory._hot_page_writable = False

    def assert_matches(self, memory: INT_Memory, vector_name: str) -> None:
        actual = list(memory.read(self.address, len(self.contents)))
        assert actual == self.contents, (
            f"Memory mismatch in {vector_name} at address {self.address}: "
            f"expected={self.contents}, actual={actual}"
        )


@dataclass(frozen=True)
class PvmPageMapStep:
    address: int
    length: int
    is_writable: bool

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PvmPageMapStep":
        return cls(
            address=int(data["address"]),
            length=int(data["length"]),
            is_writable=bool(data["is-writable"]),
        )

    def apply(self, memory: INT_Memory) -> None:
        access = Accessibility.WRITE if self.is_writable else Accessibility.READ
        memory.alter_accessibility(self.address, self.length, access)


@dataclass(frozen=True)
class PvmSetRegStep:
    reg: int
    value: int

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PvmSetRegStep":
        return cls(reg=int(data["reg"]), value=int(data["value"]))


@dataclass(frozen=True)
class PvmAssertStep:
    status: str | None = None
    regs: list[int] | None = None
    pc: int | None = None
    memory: list[PvmMemorySegment] | None = None
    gas: int | None = None
    page_fault_address: int | None = None
    hostcall: int | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PvmAssertStep":
        return cls(
            status=data.get("status"),
            regs=None if "regs" not in data else [int(x) for x in data["regs"]],
            pc=None if "pc" not in data else int(data["pc"]),
            memory=None
            if "memory" not in data
            else [PvmMemorySegment.from_json(x) for x in data["memory"]],
            gas=None if "gas" not in data else int(data["gas"]),
            page_fault_address=None
            if "page-fault-address" not in data
            else int(data["page-fault-address"]),
            hostcall=None if "hostcall" not in data else int(data["hostcall"]),
        )


@dataclass(frozen=True)
class PvmStep:
    run: bool = False
    map: PvmPageMapStep | None = None
    write: PvmMemorySegment | None = None
    set_reg: PvmSetRegStep | None = None
    assert_: PvmAssertStep | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PvmStep":
        if "run" in data:
            return cls(run=True)
        if "map" in data:
            return cls(map=PvmPageMapStep.from_json(data["map"]))
        if "write" in data:
            return cls(write=PvmMemorySegment.from_json(data["write"]))
        if "set-reg" in data:
            return cls(set_reg=PvmSetRegStep.from_json(data["set-reg"]))
        if "assert" in data:
            return cls(assert_=PvmAssertStep.from_json(data["assert"]))
        raise ValueError(f"Unknown PVM vector step: {data}")


@dataclass(frozen=True)
class PvmBlockGasCost:
    pc: int
    cost: int

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PvmBlockGasCost":
        return cls(pc=int(data["pc"]), cost=int(data["cost"]))


@dataclass(frozen=True)
class PvmStepTestcase:
    name: str
    initial_pc: int
    initial_gas: int
    program: list[int]
    steps: list[PvmStep]
    block_gas_costs: list[PvmBlockGasCost]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PvmStepTestcase":
        return cls(
            name=str(data["name"]),
            initial_pc=int(data["initial-pc"]),
            initial_gas=int(data["initial-gas"]),
            program=[int(x) for x in data["program"]],
            steps=[PvmStep.from_json(x) for x in data["steps"]],
            block_gas_costs=[
                PvmBlockGasCost.from_json(x) for x in data["block-gas-costs"]
            ],
        )


@dataclass(frozen=True)
class PvmGasOnlyTestcase:
    name: str
    program: list[int]
    block_gas_costs: list[PvmBlockGasCost]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PvmGasOnlyTestcase":
        raw_costs = data["block-gas-costs"]
        if isinstance(raw_costs, dict):
            costs = [
                PvmBlockGasCost(pc=int(pc), cost=int(cost))
                for pc, cost in raw_costs.items()
            ]
        else:
            costs = [PvmBlockGasCost.from_json(x) for x in raw_costs]
        return cls(
            name=str(data["name"]),
            program=[int(x) for x in data["program"]],
            block_gas_costs=costs,
        )


def is_step_testcase(data: dict[str, Any]) -> bool:
    return "steps" in data and "initial-regs" not in data
