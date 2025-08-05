from tsrkit_pvm.interpreter.memory import INT_Memory
from tsrkit_pvm.interpreter.program import INT_Program
from tsrkit_pvm.interpreter.pvm import Interpreter
from tsrkit_pvm.recompiler.memory import REC_Memory
import time
from tsrkit_pvm.recompiler.program import REC_Program
from tsrkit_pvm.recompiler.pvm import Recompiler
from tsrkit_pvm.recompiler.vm_context import VMContext
import json
from pathlib import Path

def execute_program_compare(bytecode: bytes, i_gas: int, r_gas: int):
    # --- Interpreter --- #
    program = INT_Program.decode(bytecode)
    start = time.time_ns()
    
    status, _, gas, _, _ = Interpreter.execute(
        program,
        0,
        i_gas,
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        INT_Memory({}, [i for i in range(10)], [i for i in range(10)]),
    )

    assert status._value_.name == "out-of-gas"

    program = REC_Program.decode(bytecode)
    int_break_time = time.time_ns()
    
    program.assemble(gas_enabled=True)

    asm_break_time = time.time_ns()

    
    status, _, gas, _, _ = Recompiler.execute(
        program,
        0,
        r_gas,
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        REC_Memory.from_initial([{"address": i, "length": 4096} for i in range(10)], [], VMContext.calculate_size(0)),
    )

    assert status._value_.name == "out-of-gas"

    return int_break_time - start, time.time_ns() - int_break_time, (1000 * len(bytecode) / (time.time_ns() - int_break_time))


def test_add_jump_loop_compare():
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

    gas = 1_000_000

    i_time, r_time, asm_inst_us = execute_program_compare(bytecode=bytecode, i_gas=gas, r_gas=gas)

    print(f"""
    \nADD_JUMP Benchmarking: 
    |  Mode  | Interpreter | Recompiler | 
    |  Time  | {(i_time / 1000000):.2f}ms | {(r_time / 1000000):.2f}ms |
    | gas/us | {(1000 * gas / i_time):.2f} gas/us | {(1000 * gas / r_time):.2f} gas/us |

    Assembling time:: {asm_inst_us} us/inst
    """)


def test_cgio_compare():

    bytecode = bytes(json.load(open(Path(__file__).parent / "programs" / "cgio.json")))
    gas = 1_000_000 

    i_time, r_time, asm_inst_us = execute_program_compare(bytecode=bytecode, i_gas=gas, r_gas=gas)

    print(f"""
    \nConwoy Game of Life Benchmarking: 
    |  Mode  | Interpreter | Recompiler | 
    |  Time  | {(i_time / 1000000):.2f}ms | {(r_time / 1000000):.2f}ms |
    | gas/us | {(1000 * gas / i_time):.2f} gas/us | {(1000 * gas / r_time):.2f} gas/us |
    
    Assembling time:: {asm_inst_us} us/inst
        """)
