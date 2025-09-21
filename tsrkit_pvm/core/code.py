from dataclasses import dataclass
import os
from typing import Tuple, Union, Any

from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable
from tsrkit_pvm.recompiler.vm_context import VMContext

from ..common.constants import PVM_INIT_DATA_SIZE, PVM_INIT_ZONE_SIZE

from ..recompiler.program import REC_Program
from ..recompiler.memory import REC_Memory
from tsrkit_pvm.interpreter.program import INT_Program
from tsrkit_pvm.interpreter.memory import INT_Memory
from ..cpvm.cy_memory import CyMemory
from ..cpvm.cy_program import CyProgram

_PVM_MODE = os.environ.get("PVM_MODE", "interpreter")

@dataclass
class Code(Codable):
    """
    This defines the structure the bytecode. Build using program code, read & write data and stack size.
    Combined with args, this gives us memory and registers needed for execution.
    """

    read: bytes
    r_write: bytes
    code: bytes
    z: int
    s: int

    @classmethod
    def decode_from(cls, pc: bytes) -> Union[None, "Code"]:
        offset = 0
        o_len, decoded = int.from_bytes(pc[offset : offset + 3], "little"), 3
        offset += decoded
        w_len, decoded = int.from_bytes(pc[offset : offset + 3], "little"), 3
        offset += decoded
        z, decoded = int.from_bytes(pc[offset : offset + 2], "little"), 2
        offset += decoded
        s, decoded = int.from_bytes(pc[offset : offset + 3], "little"), 3
        offset += decoded
        # `o` (read-only data)
        o = pc[offset : offset + o_len]
        offset += o_len
        # `w` (read-write data)
        w = pc[offset : offset + w_len]
        offset += w_len
        # Code blobs
        c_len, decoded = int.from_bytes(pc[offset : offset + 4], "little"), 4
        offset += decoded
        c = pc[offset : offset + c_len]
        offset += c_len
        return cls(read=o, r_write=w, z=z, s=s, code=c)

    def encode_size(self) -> int:
        return 3 + 3 + 2 + 3 + len(self.read) + len(self.r_write) + 4 + len(self.code)

    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        start = offset

        offset += Uint[24](len(self.read)).encode_into(buffer, offset)

        offset += Uint[24](len(self.r_write)).encode_into(buffer, offset)

        offset += Uint[16](self.z).encode_into(buffer, offset)

        offset += Uint[24](self.s).encode_into(buffer, offset)

        buffer[offset : offset + len(self.read)] = self.read
        offset += len(self.read)

        buffer[offset : offset + len(self.r_write)] = self.r_write
        offset += len(self.r_write)

        offset += Uint[32](len(self.code)).encode_into(buffer, offset)

        buffer[offset : offset + len(self.code)] = self.code
        offset += len(self.code)

        return offset - start


def regs_from_pc(args: bytes) -> list:
    result = [0] * 13
    result[0] = 2**32 - 2**16
    result[1] = 2**32 - 2 * PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE
    result[7] = 2**32 - PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE
    result[8] = len(args)
    return result


def y_function(
    bytecode: bytes, args: bytes
) -> Union[Tuple[Any, list, Any], None]:
    """Extract program components from bytecode.

    Returns:
        Tuple of (program, registers, memory_data)
    """
    code = Code.decode_from(bytecode)
    if not code:
        return None

    
    if _PVM_MODE == "recompiler":
        program_ = REC_Program.decode_from(code.code)[0]
        memory = REC_Memory.from_pc(
            code.read,
            code.r_write,
            args,
            code.z,
            code.s,
            VMContext.calculate_size(len(program_.jump_table)),
        )
    elif _PVM_MODE == "mypyc":
        program_ = INT_Program.decode_from(code.code)[0]
        memory = INT_Memory.from_pc(code.read, code.r_write, args, code.z, code.s)
    elif _PVM_MODE == "interpreter":
        program_ = CyProgram.decode_from(code.code)[0]
        memory = CyMemory.from_pc(code.read, code.r_write, args, code.z, code.s)
    else:
        raise ValueError(f"PVM_MODE {_PVM_MODE} not supported")

    return (
        program_,
        regs_from_pc(args),
        memory,
    )
