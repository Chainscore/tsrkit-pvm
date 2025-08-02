from tsrkit_asm import (
    PyAssembler,
    RegMem,
    Size,
    Reg,
    LoadKind,
    RegSize,
    MemOp,
)
from tsrkit_pvm.recompiler.assembler.utils import (
    load_all_regs,
    pop_all_regs,
    push_all_regs,
    save_all_regs,
)
from tsrkit_pvm.recompiler.fn_alloc import allocate_executable_memory
from tsrkit_pvm.recompiler.vm_context import (
    r_map,
    regs_offset,
    ret_stack_offset,
    TEMP_REG,
)


def create_caller(code_pointer: int, mem_pointer: int, vm_size: int):
    asm = PyAssembler()

    # RCX –> code pointer,  R15 –> pointer to VMContext struct
    asm.mov_imm64(TEMP_REG, code_pointer)
    asm.mov_imm64(Reg.r15, mem_pointer)  # Base pointer to linear PVM memory

    # ----------------------------------------------------------
    # Guest-register mapping
    # ----------------------------------------------------------
    push_all_regs(asm)
    load_all_regs(asm)

    # call the generated program
    asm.call(RegMem.Reg(TEMP_REG))

    # ----------------------------------------------------------
    # Store back the results
    # ----------------------------------------------------------
    save_all_regs(asm)
    pop_all_regs(asm)

    asm.ret()

    thunk = asm.finalize()
    buf, addr = allocate_executable_memory(thunk)
    return addr, buf
