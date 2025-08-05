from copy import copy
from os import write
from pathlib import Path

from tsrkit_types import Bytes, Uint

from tsrkit_pvm.core.code import y_function
from tsrkit_pvm.interpreter.program import INT_Program
from tsrkit_pvm.interpreter.pvm import Interpreter
from tsrkit_pvm.recompiler.program import REC_Program
from tsrkit_pvm.recompiler.pvm import Recompiler


def test_jam_refine():
    service = "hello"
    payload = b"Prasad"

    service = "counter"
    payload = b"inc"
    args = bytes.fromhex(
        "0103696e63656511d605df64d1d171e9a8590eb7b38dfe12ea4222dd30cfe057e7f03cecc0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002bc99745f0c6b09bc54c7bf43a8598100056eccc33a09ec887594669cafac63b"
    )

    service_code = open(
        Path(__file__).parents[3]
        / "test-suite"
        / "playground"
        / "builds"
        / f"{service}-service.jam",
        "rb",
    ).read()
    metadata, m_len = Bytes.decode_from(service_code)
    bytecode = service_code[m_len:]

    gas = 10000
    pc = 0

    while True:
        print(f"=== Step {gas} ===")
        # --- Interpreter Mode --- #
        code, regs, mem = y_function(bytecode, args, "interpreter")
        i_status, i_pc, i_gas, i_regs, i_mem = Interpreter.execute(
            INT_Program.decode(code), copy(pc), gas, regs, mem
        )

        print(
            f"""
              Status: {i_status}
              Gas: {i_gas}
              PC: {i_pc}
              Regs: {i_regs}
              """
        )

        # --- Recompiler Mode --- #
        code, regs, mem = y_function(bytecode, args, "recompiler")
        if i_status._value_.name == "host" and i_status._value_.register == 2**64 - 1:
            print("INT_SBRK")
        r_status, r_pc, r_gas, r_regs, r_mem = Recompiler.execute(
            REC_Program.decode(code), copy(pc), gas, regs, mem
        )

        print(
            f"""
              Status: {r_status}
              Gas: {r_gas}
              PC: {r_pc}
              Regs: {r_regs}
              """
        )

        assert i_status == r_status
        assert i_gas == r_gas
        assert i_regs == r_regs, f"Mismatch at {gas}"

        if i_status._value_.name == "halt":
            print("Reached HALT")
            break
        gas += 1
