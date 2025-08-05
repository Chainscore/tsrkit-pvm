"""Test package structure and imports."""

import time
from tsrkit_pvm.interpreter.memory import Memory
from tsrkit_pvm.interpreter.program import INT_Program
from tsrkit_pvm.interpreter.pvm import PVM
from tsrkit_pvm.common.status import ExecutionStatus
from tsrkit_pvm.recompiler.memory import REC_Memory
from tsrkit_pvm.recompiler.program import REC_Program
from tsrkit_pvm.recompiler.pvm import Recompiler
from tsrkit_pvm.recompiler.vm_context import VMContext
from pathlib import Path
import json


def test_benched_cgoi_recompiler():
    """
    Benchmarking with Conway Game of Life

    05Aug25:
    - python:    gas/us

    --------------------------------

    """
    bytecode = bytes(json.load(open(Path(__file__).parent / "programs" / "cgio.json")))
    program = REC_Program.decode_from(bytecode)[0]
    program.assemble()
    regs = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    gas = 100000
    start_time = time.time_ns()
    ret = Recompiler.execute(
        program,
        0,
        gas,
        regs,
        REC_Memory(VMContext.calculate_size(len(program.jump_table))),
    )
    assert ret[0] == ExecutionStatus.OUT_OF_GAS
    end_time = time.time_ns()
    print(f"PVM - CGOI: {1000 * gas/(end_time - start_time)} gas/us")


def test_add_jump():
    """
    Benchmarking a simple infinite add and jump program

    21Jun25:
    - python:    0.6783694440694569 gas/us
    - pypy3:     16.06864525251876 gas/us

    --------------------------------

    """
    bytecode = bytes(
        [0, 0, 14, 40, 2, 200, 50, 1, 40, 2, 200, 67, 2, 51, 1, 40, 246, 165, 20]
    )
    program = REC_Program.decode_from(bytecode)[0]
    program.assemble()
    regs = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    gas = 100_000
    start_time = time.time_ns()
    ret = Recompiler.execute(
        program,
        0,
        gas,
        regs,
        REC_Memory(VMContext.calculate_size(0)),
    )
    assert ret[0] == ExecutionStatus.OUT_OF_GAS
    end_time = time.time_ns()
    print(
        f"\nPVM - ADD JUMP GAS EXAUST {gas}: {1000 * gas/(end_time - start_time)}%s gas/us"
    )


def test_add_jump_loop_1_000_000():
    """
    Benchmarking a looped add and jump program

    24Jun25:
    - python:   0.6251248025962577 gas/us
    - pypy3:    NA gas/us

    --------------------------------

    """
    bytecode = bytes(
        [
            0,
            0,
            26,
            51,
            0,
            51,
            1,
            64,
            66,
            15,
            40,
            2,
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
            133,
            146,
            0,
            2,
        ]
    )
    program = REC_Program.decode(bytecode)
    program.assemble()
    regs = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    gas = 1_000_000
    start_time = time.time_ns()
    ret = Recompiler.execute(program, 0, gas, regs, REC_Memory(VMContext.calculate_size(0)))
    assert ret[0] == ExecutionStatus.OUT_OF_GAS
    end_time = time.time_ns()
    gas_consumed = gas - ret[2]
    print(f"Gas consumed:", gas_consumed)
    print(
        f"PVM - ADD LOOP 1,000,000: {1000 * gas_consumed/(end_time - start_time)} gas/us | Total time {(end_time - start_time) / (10**6)} ms"
    )
