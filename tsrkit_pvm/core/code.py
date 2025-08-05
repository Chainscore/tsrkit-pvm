from dataclasses import dataclass
from typing import Any, Self, Tuple, Type

from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable

from tsrkit_pvm.core import program_base
from tsrkit_pvm.core.memory import Memory
from tsrkit_pvm.core.program_base import Program
from tsrkit_pvm.interpreter.memory import INT_Memory
from tsrkit_pvm.recompiler.memory import REC_Memory
from tsrkit_pvm.recompiler.vm_context import VMContext

from ..common.constants import PVM_INIT_DATA_SIZE, PVM_INIT_ZONE_SIZE


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
    def decode_from(cls, pc: bytes) -> None | Self:
        offset = 0
        o_len, decoded = Uint[24].decode_from(pc, offset)
        offset += decoded
        w_len, decoded = Uint[24].decode_from(pc, offset)
        offset += decoded
        z, decoded = Uint[16].decode_from(pc, offset)
        offset += decoded
        s, decoded = Uint[24].decode_from(pc, offset)
        offset += decoded
        # `o` (read-only data)
        o = pc[offset : offset + o_len]
        offset += o_len
        # `w` (read-write data)
        w = pc[offset : offset + w_len]
        offset += w_len
        # Code blobs
        c_len, decoded = Uint[32].decode_from(pc, offset)
        offset += decoded
        c = pc[offset : offset + c_len]
        offset += c_len
        return cls(read=o, r_write=w, z=z, s=s, code=c)

    def encode_size(self):
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


def regs_from_pc(args) -> list:
    result = [0] * 13
    result[0] = 2**32 - 2**16
    result[1] = 2**32 - 2 * PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE
    result[7] = 2**32 - PVM_INIT_ZONE_SIZE - PVM_INIT_DATA_SIZE
    result[8] = len(args)
    return result


def y_function(
    bytecode: bytes, args: bytes, mode="recompiler"
) -> Tuple[bytes, list, Memory]:
    """Extract program components from bytecode.

    Returns:
        Tuple of (program_code, registers, memory_data)
    """
    code = Code.decode_from(bytecode)

    program_ = program_base.Program.decode_from(code.code)[0]

    if mode == "recompiler":
        memory = REC_Memory.from_pc(
            code.read,
            code.r_write,
            args,
            code.z,
            code.s,
            VMContext.calculate_size(len(program_.jump_table)),
        )
    else:
        memory = INT_Memory.from_pc(code.read, code.r_write, args, code.z, code.s)

    return (
        code.code,
        regs_from_pc(args),
        memory,
    )
