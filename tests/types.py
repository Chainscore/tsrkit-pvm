from dataclasses import field
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
            if page.is_writable:
                allowed_write_pages.append(page.address // 2**12)
                allowed_read_pages.append(page.address // 2**12)
            else:
                allowed_read_pages.append(page.address // 2**12)

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
            if page.is_writable:
                allowed_write_pages.append(page.address // 2**12)
                allowed_read_pages.append(page.address // 2**12)
            else:
                allowed_read_pages.append(page.address // 2**12)

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
