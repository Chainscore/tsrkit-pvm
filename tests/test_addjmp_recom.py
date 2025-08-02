from tsrkit_pvm.recompiler.memory import REC_Memory
from tsrkit_pvm.recompiler.program import REC_Program
from tsrkit_pvm.recompiler.pvm import Recompiler
from tsrkit_pvm.recompiler.vm_context import VMContext


def test_add_jump_loop_1_000_000():
    """
    Benchmarking a looped add and jump program

    24Jun25:
    - python:   2838 gas/us

    --------------------------------

    """
    bytecode = bytes(
        [
            0,
            0,
            17,
            149,
            0,
            1,
            171,
            16,
            253,
            20,
            3,
            239,
            190,
            173,
            222,
            0,
            0,
            0,
            0,
            0,
            73,
            0,
            1,
        ]
    )
    program = REC_Program.decode(bytecode)

    Recompiler.execute(
        program,
        0,
        100000,
        [0, 1_000_000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        REC_Memory.from_initial([], [], VMContext.calculate_size(0)),
    )
