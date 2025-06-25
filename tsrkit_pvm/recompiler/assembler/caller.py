from py_asm import *
from py_asm import LOAD_U64
from tsrkit_pvm.recompiler.assembler.inst_map import inst_map
from tsrkit_pvm.recompiler.assembler.instruction_table import InstructionTable
from tsrkit_pvm.recompiler.fn_alloc import allocate_executable_memory
import ctypes
from tsrkit_pvm.recompiler.vm_context import r_map

def create_caller(code_pointer: int, vm_pointer: int):
    asm = PyAssembler()
    
    # Save RCX, RBX, RBP, R15
    regs_to_save = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    for i in regs_to_save:
        asm.push(i)

    # RCX –> code pointer,  R15 –> pointer to VMContext struct
    asm.mov_imm64(RCX, code_pointer)
    asm.mov_imm64(R15, vm_pointer)

    # ----------------------------------------------------------
    # Guest-register mapping
    # ----------------------------------------------------------
    
    for key, val in r_map.items():
        asm.load(LOAD_U64, val, 0, 64, R15, key * 8) # Mapped Reg <- regs[0]

    # call the generated program
    asm.call_reg(RCX)

    # ----------------------------------------------------------
    # store back the results
    # ----------------------------------------------------------
    for key, val in r_map.items():
        asm.store(8, 0, 64, R15, key * 8, val)
    
    for i in reversed(regs_to_save):
        asm.pop(i)
    
    asm.ret()

    thunk = asm.finalize()
    buf, addr = allocate_executable_memory(thunk)
    FUNC = ctypes.CFUNCTYPE(ctypes.c_uint64)
    func = FUNC(addr)
    setattr(func, "_exec_buf", buf)                   # pin buffer
    return func

