from tsrkit_types import U64, TypedArray
from tsrkit_pvm.recompiler.memory import GuestMemory
from tsrkit_pvm.recompiler.program import Program
import time

from tsrkit_pvm.recompiler.pvm import PVM
from tsrkit_pvm.recompiler.vm_context import VMContext

def test_add_jump_loop_1_000_000():
    """
    Benchmarking a looped add and jump program

    24Jun25:
    - python:   2838 gas/us

    --------------------------------
    
    """
    bytecode = bytes([0,0,17,149,0,1,171,16,253,20,3,239,190,173,222,0,0,0,0,0,73,0,1])
    program = Program.decode(bytecode)


    PVM.execute(
        program,
        GuestMemory.from_initial([], [], VMContext.calculate_size(0)),
        0,
        [0, 1_000_000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        100000
    )
