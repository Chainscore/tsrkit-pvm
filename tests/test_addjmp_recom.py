from tsrkit_types import U64, TypedArray
from tsrkit_pvm.interpreter.program import Program
import time

from tsrkit_pvm.recompiler.assembler.asm import assemble
from tsrkit_pvm.recompiler.pvm import PVM

def test_add_jump_loop_1_000_000():
    """
    Benchmarking a looped add and jump program

    24Jun25:
    - python:   NA gas/us
    - pypy3:    NA gas/us

    --------------------------------
    
    """
    bytecode = bytes([0,0,26,51,0,51,1,64,66,15,40,2,149,0,1,171,16,253,20,3,239,190,173,222,0,0,0,0,0,133,146,0,2])
    program = Program.decode(bytecode)

    PVM.execute(
        program, 
        TypedArray[U64, 4]([U64(0), U64(0), U64(0), U64(0)]), 
        100000
    )
    
    # regs = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    #
    # gas = 1_000_000_000
    # start_time = time.time_ns()
    # ret = PVM.execute(program, 0, gas, regs, Memory({}, [], []))
    # assert ret[0] == ExecutionStatus.PANIC
    # end_time = time.time_ns()
    # gas_consumed = gas - ret[2]
    # print(f"PVM - ADD LOOP 1,000,000: {1000 * gas_consumed/(end_time - start_time)} gas/us | Total time {(end_time - start_time) / (10**6)} ms")
