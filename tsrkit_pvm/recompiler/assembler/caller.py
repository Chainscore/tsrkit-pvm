from tsrkit_asm import (
    PyAssembler,
    RegMem,
    Size,
    Reg,
    LoadKind,
    RegSize,
    MemOp,
)
from tsrkit_pvm.recompiler.fn_alloc import allocate_executable_memory
import ctypes
from tsrkit_pvm.recompiler.vm_context import r_map, regs_offset, ret_stack_offset


def create_caller(code_pointer: int, mem_pointer: int, vm_size: int):
    asm = PyAssembler()

    # Save all registers
    for i in r_map:
        asm.push(i)

    # RCX –> code pointer,  R15 –> pointer to VMContext struct
    asm.mov_imm64(Reg.rcx, code_pointer)
    asm.mov_imm64(Reg.r15, mem_pointer)  # Base pointer to linear PVM memory 

    # ----------------------------------------------------------
    # Guest-register mapping
    # ----------------------------------------------------------
    for i, reg in enumerate(r_map):
        # Load value from offset+i_bytes -> mapped register
        asm.load(
            kind=LoadKind.U64,
            reg=reg,
            mem=MemOp.BaseOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                # Reversed 13 registers, and gas
                offset=(regs_offset + i * 8),
            ),
        )

    asm.store(
        Size.U64,
        MemOp.BaseOffset(
            seg=None,
            size=RegSize.R64,
            base=Reg.r15,
            offset=ret_stack_offset
        ), 
        Reg.rsp
    )

    # call the generated program
    asm.call(RegMem.Reg(Reg.rcx))

    ret_label = asm.current_address()
    # ----------------------------------------------------------
    # store back the results
    # ----------------------------------------------------------
    for i, reg in enumerate(r_map):
        asm.store(
            size=Size.U64,
            mem=MemOp.BaseOffset(
                seg=None, size=RegSize.R64, base=Reg.r15, offset=(regs_offset + i * 8)
            ),
            reg=reg,
        )

    for i in reversed(r_map):
        asm.pop(i)
    
    asm.ret()

    thunk = asm.finalize()
    buf, addr = allocate_executable_memory(thunk)
    return addr, ret_label, buf
