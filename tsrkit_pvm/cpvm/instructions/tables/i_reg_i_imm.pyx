# cython: boundscheck=False, wraparound=False, cdivision=True
"""
Cython optimized instruction table for 1 register + 1 immediate argument instructions.

This table handles instructions that take one register and one immediate argument:
- jump_ind: Indirect jump
- load_imm: Load immediate value
- load_u8/i8/u16/i16/u32/i32/u64: Load from memory
- store_u8/u16/u32/u64: Store to memory
"""

from typing import Dict
from libc.stdint cimport uint32_t, uint64_t

from tsrkit_pvm.common.status import CONTINUE
from tsrkit_pvm.common.utils import chi, clamp_12, clamp_4
from tsrkit_pvm.core.opcode import OpCode
from ...cy_memory cimport CyMemory


cdef class CyInstructionsWArgs1Reg1Imm:
    """
    Cython optimized instruction table for 1 register + 1 immediate argument instructions.
    
    This class provides high-performance implementations of instructions that
    take one register and one immediate argument, optimized with Cython for speed.
    """
    
    cdef public uint32_t counter
    cdef public object program  # INT_Program - keeping as Python object for now
    cdef public uint32_t skip_index
    
    def __init__(self, uint32_t counter, program, uint32_t skip_index):
        self.counter = counter
        self.program = program
        self.skip_index = skip_index

    cpdef list get_props(self):
        """
        Extract register and immediate arguments from the instruction stream.
        Returns [ra, lx, vx] where ra is register, lx is length, vx is the immediate value.
        """
        cdef uint32_t lx = clamp_4(max(0, self.skip_index - 1))
        cdef bytes zeta_slice = self.program.zeta[self.counter + 1: self.counter + 1 + 1 + lx]
        cdef uint32_t ra = clamp_12(zeta_slice[0] % 16)
        temp_vx = chi(int.from_bytes(zeta_slice[1:9], "little"), lx)
        cdef uint64_t vx = <uint64_t>(temp_vx & 0xFFFFFFFFFFFFFFFF)
        return [ra, lx, vx]

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        """Return the instruction table mapping opcodes to their handlers."""
        return {
            50: OpCode(name="jump_ind", fn=cls.jump_ind, gas=1, is_terminating=True),
            51: OpCode(name="load_imm", fn=cls.load_imm, gas=1, is_terminating=False),
            52: OpCode(name="load_u8", fn=cls.load_u8, gas=1, is_terminating=False),
            53: OpCode(name="load_i8", fn=cls.load_i8, gas=1, is_terminating=False),
            54: OpCode(name="load_u16", fn=cls.load_u16, gas=1, is_terminating=False),
            55: OpCode(name="load_i16", fn=cls.load_i16, gas=1, is_terminating=False),
            56: OpCode(name="load_u32", fn=cls.load_u32, gas=1, is_terminating=False),
            57: OpCode(name="load_i32", fn=cls.load_i32, gas=1, is_terminating=False),
            58: OpCode(name="load_u64", fn=cls.load_u64, gas=1, is_terminating=False),
            59: OpCode(name="store_u8", fn=cls.store_u8, gas=1, is_terminating=False),
            60: OpCode(name="store_u16", fn=cls.store_u16, gas=1, is_terminating=False),
            61: OpCode(name="store_u32", fn=cls.store_u32, gas=1, is_terminating=False),
            62: OpCode(name="store_u64", fn=cls.store_u64, gas=1, is_terminating=False),
        }

    cdef tuple  jump_ind(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC50: Indirect jump to address in register + offset."""
        status, counter = self.program.djump( 
            self.counter, (int(registers[ra]) + vx) % 2**32
        )
        return status, counter

    cdef tuple  load_imm(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC51: Load immediate value into register."""
        registers[ra] = vx
        return CONTINUE, -1

    cdef tuple  load_u8(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC52: Load unsigned 8-bit value from memory."""
        cdef bytes data = memory.read(vx & 0xFFFFFFFF, 1)
        registers[ra] = int.from_bytes(data, "little")
        return CONTINUE, -1

    cdef tuple  load_i8(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC53: Load signed 8-bit value from memory."""
        cdef bytes data = memory.read(vx & 0xFFFFFFFF, 1)
        registers[ra] = chi(int.from_bytes(data, "little"), 1)
        return CONTINUE, -1

    cdef tuple  load_u16(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC54: Load unsigned 16-bit value from memory."""
        cdef bytes data = memory.read(vx & 0xFFFFFFFF, 2)
        registers[ra] = int.from_bytes(data, "little")
        return CONTINUE, -1

    cdef tuple  load_i16(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC55: Load signed 16-bit value from memory."""
        cdef bytes data = memory.read(vx & 0xFFFFFFFF, 2)
        registers[ra] = chi(int.from_bytes(data, "little"), 2)
        return CONTINUE, -1

    cdef tuple  load_u32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC56: Load unsigned 32-bit value from memory."""
        cdef bytes data = memory.read(vx & 0xFFFFFFFF, 4)
        registers[ra] = int.from_bytes(data, "little")
        return CONTINUE, -1

    cdef tuple  load_i32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC57: Load signed 32-bit value from memory."""
        cdef bytes data = memory.read(vx & 0xFFFFFFFF, 4)
        registers[ra] = chi(int.from_bytes(data, "little"), 4)
        return CONTINUE, -1

    cdef tuple  load_u64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC58: Load unsigned 64-bit value from memory."""
        cdef bytes data = memory.read(vx & 0xFFFFFFFF, 8)
        registers[ra] = int.from_bytes(data, "little")
        return CONTINUE, -1

    cdef tuple  store_u8(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC59: Store register value as unsigned 8-bit to memory."""
        memory.write(vx & 0xFFFFFFFF, (registers[ra] % 256).to_bytes(1, "little"))
        return CONTINUE, -1

    cdef tuple  store_u16(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC60: Store register value as unsigned 16-bit to memory."""
        memory.write(vx & 0xFFFFFFFF, (registers[ra] % 65536).to_bytes(2, "little"))
        return CONTINUE, -1

    cdef tuple  store_u32(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC61: Store register value as unsigned 32-bit to memory."""
        memory.write(vx & 0xFFFFFFFF, (registers[ra] % 4294967296).to_bytes(4, "little"))
        return CONTINUE, -1

    cdef tuple  store_u64(self, uint64_t *registers, CyMemory memory, uint32_t ra, uint32_t lx, uint64_t vx):
        """OPC62: Store register value as unsigned 64-bit to memory."""
        memory.write(vx & 0xFFFFFFFF, (registers[ra] % 18446744073709551616).to_bytes(8, "little"))
        return CONTINUE, -1

