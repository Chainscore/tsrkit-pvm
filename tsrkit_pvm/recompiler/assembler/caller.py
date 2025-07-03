from tsrkit_asm import PyAssembler, RegIndex, RegMem, Size, Reg, LoadKind, SegReg, RegSize, MemOp
from tsrkit_pvm.recompiler.fn_alloc import allocate_executable_memory
import ctypes
from tsrkit_pvm.recompiler.vm_context import r_map

def create_caller(code_pointer: int, mem_pointer: int):
    asm = PyAssembler()
    
    # Save all registers
    for i in r_map:
        asm.push(i)

    # RCX –> code pointer,  R15 –> pointer to VMContext struct
    asm.mov_imm64(Reg.rcx, code_pointer)
    asm.mov_imm64(Reg.r15, mem_pointer)      # Base pointer to linear PVM memory

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
                offset=(-(13-i)*8 - 8)
            )
        )

    # call the generated program
    asm.call(RegMem.Reg(Reg.rcx))

    # ----------------------------------------------------------
    # store back the results
    # ----------------------------------------------------------
    for i, reg in enumerate(r_map):        
        asm.store(
            size=Size.U64, 
            mem=MemOp.BaseOffset(
                seg=None, 
                size=RegSize.R64, 
                base=Reg.r15, 
                offset=(-(13 - i)*8 - 8)
            ), 
            reg=reg
        )
    
    for i in reversed(r_map):
        asm.pop(i)
    
    asm.ret()

    thunk = asm.finalize()
    buf, addr = allocate_executable_memory(thunk)
    FUNC = ctypes.CFUNCTYPE(ctypes.c_uint64)
    func = FUNC(addr)
    setattr(func, "_exec_buf", buf)                   # pin buffer
    return func

