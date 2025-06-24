from tsrkit_pvm.interpreter.program import Program
from py_asm import *
from py_asm import LOAD_U64
from tsrkit_pvm.recompiler.assembler.inst_map import inst_map
from tsrkit_pvm.recompiler.assembler.instruction_table import InstructionTable
from tsrkit_pvm.recompiler.fn_alloc import allocate_executable_memory
import ctypes


class AssemblerContext:
    """Wrapper to provide context for the assembler"""
    def __init__(self, assembler, labels, program):
        self.asm = assembler
        self.labels = labels
        self.program = program
    
    def __getattr__(self, name):
        # Delegate all other attributes to the underlying assembler
        return getattr(self.asm, name)

def assemble(program: Program) -> bytes:
    asm = PyAssembler()
    
    # Create labels for all basic blocks (jump targets)
    labels = {}
    for block_start in program.basic_blocks:
        if block_start < len(program.instruction_set):
            labels[block_start] = asm.forward_declare_label()
    
    # Create context wrapper
    asm_ctx = AssemblerContext(asm, labels, program)

    counter = 0
    while counter < len(program.instruction_set):
        if program.offset_bitmask[counter]:  # Only process actual opcodes
            # Define label if this is a basic block start
            if counter in labels:
                asm.define_label(labels[counter])
                
            opcode = program.instruction_set[counter]
            print(f"Running opcode {opcode} at position {counter}")
            inst_map.execute_instruction(opcode, program, counter, asm_ctx)
        counter += 1

    return asm.finalize()


def create_callable_function(code_pointer: int, vm_pointer: int):
    asm = PyAssembler()

    # RCX –> code pointer,  R15 –> pointer to VMContext struct
    asm.mov_imm64(RCX, code_pointer)
    asm.mov_imm64(R15, vm_pointer)

    # ----------------------------------------------------------
    # Guest-register mapping (examples, adapt as you need)
    # load  [R15 + 0]  into RDI   (regs[0])
    # load  [R15 + 8]  into RAX   (regs[1])
    # ----------------------------------------------------------
    asm.push(RAX)                                     # save caller RAX
    asm.load(LOAD_U64, RDI, 0, 64, R15, 0)            # RDI <- regs[0]
    asm.load(LOAD_U64, RAX, 0, 64, R15, 8)            # RAX <- regs[1]
    asm.load(LOAD_U64, RSI, 0, 64, R15, 16)            # RAX <- regs[1]
    asm.load(LOAD_U64, RBX, 0, 64, R15, 24)            # RAX <- regs[1]

    # call the generated program
    asm.call_reg(RCX)

    # ----------------------------------------------------------
    # store back the results
    # store RDI -> [R15 + 0]
    # store RAX -> [R15 + 8]
    # ----------------------------------------------------------
    asm.store(8, 0, 64, R15, 0, RDI)
    asm.store(8, 0, 64, R15, 8, RAX)
    asm.store(8, 0, 64, R15, 16, RSI)
    asm.store(8, 0, 64, R15, 24, RBX)
    asm.pop(RAX)                                      # restore caller RAX

    asm.ret()

    thunk = asm.finalize()
    buf, addr = allocate_executable_memory(thunk)
    FUNC = ctypes.CFUNCTYPE(ctypes.c_uint64)
    func = FUNC(addr)
    setattr(func, "_exec_buf", buf)                   # pin buffer
    return func

