"""Test package structure and imports."""

import time
from tsrkit_pvm.interpreter.memory import Memory
from tsrkit_pvm.interpreter.program import INT_Program
from tsrkit_pvm.interpreter.pvm import PVM
from tsrkit_pvm.common.status import ExecutionStatus


def test_benched_cgoi_interpreter():
    """
    Benchmarking with COnway Game of Life

    21Jun25:
    - python:   0.14730875015449005 gas/us
    - pypy:     0.8381133732722292 gas/us

    --------------------------------

    """
    bytecode = bytes(
        [
            0,
            0,
            129,
            23,
            30,
            1,
            3,
            255,
            0,
            30,
            1,
            11,
            255,
            0,
            30,
            1,
            19,
            255,
            0,
            30,
            1,
            18,
            255,
            0,
            30,
            1,
            9,
            255,
            0,
            40,
            233,
            0,
            51,
            1,
            255,
            1,
            149,
            17,
            1,
            81,
            17,
            8,
            223,
            0,
            51,
            2,
            255,
            1,
            149,
            34,
            1,
            81,
            18,
            8,
            241,
            150,
            19,
            8,
            200,
            35,
            3,
            40,
            47,
            149,
            51,
            128,
            0,
            124,
            52,
            132,
            68,
            1,
            82,
            20,
            1,
            14,
            83,
            21,
            2,
            25,
            86,
            21,
            3,
            21,
            40,
            8,
            81,
            21,
            3,
            6,
            40,
            11,
            149,
            51,
            128,
            70,
            3,
            255,
            0,
            40,
            205,
            149,
            51,
            128,
            70,
            3,
            40,
            198,
            51,
            5,
            100,
            52,
            51,
            8,
            64,
            149,
            68,
            255,
            205,
            132,
            7,
            149,
            119,
            128,
            0,
            124,
            118,
            132,
            102,
            1,
            200,
            101,
            5,
            149,
            68,
            2,
            205,
            132,
            7,
            149,
            119,
            128,
            0,
            124,
            118,
            132,
            102,
            1,
            200,
            101,
            5,
            149,
            68,
            247,
            205,
            132,
            7,
            149,
            119,
            128,
            0,
            124,
            118,
            132,
            102,
            1,
            200,
            101,
            5,
            149,
            68,
            16,
            205,
            132,
            7,
            149,
            119,
            128,
            0,
            124,
            118,
            132,
            102,
            1,
            200,
            101,
            5,
            149,
            68,
            1,
            205,
            132,
            7,
            149,
            119,
            128,
            0,
            124,
            118,
            132,
            102,
            1,
            200,
            101,
            5,
            149,
            68,
            254,
            205,
            132,
            7,
            149,
            119,
            128,
            0,
            124,
            118,
            132,
            102,
            1,
            200,
            101,
            5,
            149,
            68,
            240,
            205,
            132,
            7,
            149,
            119,
            128,
            0,
            124,
            118,
            132,
            102,
            1,
            200,
            101,
            5,
            149,
            68,
            2,
            205,
            132,
            7,
            149,
            119,
            128,
            0,
            124,
            118,
            132,
            102,
            1,
            200,
            101,
            5,
            40,
            60,
            255,
            51,
            1,
            1,
            149,
            19,
            128,
            0,
            128,
            18,
            122,
            50,
            149,
            17,
            4,
            81,
            17,
            64,
            12,
            255,
            40,
            240,
            33,
            132,
            16,
            146,
            9,
            153,
            72,
            138,
            18,
            17,
            69,
            137,
            82,
            149,
            36,
            74,
            146,
            40,
            73,
            162,
            36,
            137,
            146,
            36,
            74,
            146,
            40,
            73,
            162,
            36,
            137,
            146,
            52,
            42,
            33,
        ]
    )
    program = INT_Program.decode_from(bytecode)[0]
    regs = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    gas = 100
    start_time = time.time_ns()
    ret = PVM.execute(
        program,
        0,
        gas,
        regs,
        Memory({}, [i for i in range(10)], [i for i in range(10)]),
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
    program = INT_Program.decode_from(bytecode)[0]
    regs = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    gas = 100_000
    start_time = time.time_ns()
    ret = PVM.execute(
        program,
        0,
        gas,
        regs,
        Memory({}, [i for i in range(10)], [i for i in range(10)]),
    )
    assert ret[0] == ExecutionStatus.OUT_OF_GAS
    end_time = time.time_ns()
    print(
        f"PVM - ADD JUMP GAS EXAUST {gas}: {1000 * gas/(end_time - start_time)} gas/us"
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
    program = INT_Program.decode(bytecode)
    regs = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    gas = 1_000_000
    start_time = time.time_ns()
    ret = PVM.execute(program, 0, gas, regs, Memory({}, [], []))
    assert ret[0] == ExecutionStatus.OUT_OF_GAS
    end_time = time.time_ns()
    gas_consumed = gas - ret[2]
    print(f"Gas consumed:", gas_consumed)
    print(
        f"PVM - ADD LOOP 1,000,000: {1000 * gas_consumed/(end_time - start_time)} gas/us | Total time {(end_time - start_time) / (10**6)} ms"
    )
