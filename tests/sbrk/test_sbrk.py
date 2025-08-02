"""Test the sbrk (system break) instruction implementation."""

import pytest
from tests.sbrk.utils import create_sbrk_test_program
from tsrkit_pvm.interpreter.memory import INT_Memory
from tsrkit_pvm.interpreter.program import INT_Program
from tsrkit_pvm.common.status import ExecutionStatus
from tsrkit_pvm.interpreter.pvm import Interpreter
from tsrkit_pvm.recompiler.program import REC_Program
from tsrkit_pvm.recompiler.pvm import Recompiler
from tsrkit_pvm.recompiler.memory import REC_Memory
from tsrkit_pvm.recompiler.vm_context import VMContext


def test_sbrk_interpreter_basic():
    """Test sbrk instruction with interpreter - basic allocation."""
    # Test: allocate 1024 bytes, rd=1, ra=2
    program = create_sbrk_test_program(rd=1, ra=2)

    # Initial registers: ra=2 contains 1024 (bytes to allocate)
    initial_registers = [0, 0, 1024, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    # Initial memory with some writable pages
    initial_memory = INT_Memory({}, [], [])
    initial_heap_break = initial_memory.heap_break

    # Execute
    status, pc, gas_left, final_registers, final_memory = Interpreter.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )

    # Focus on register values - rd (register 1) should contain the new heap break
    # The interpreter should execute sbrk and update both the register and memory
    print(f"Status: {status}, Final registers: {final_registers}")
    print(
        f"Initial heap break: {initial_heap_break}, Final heap break: {final_memory.heap_break}"
    )

    # Verify rd (register 1) was modified (should contain new heap break)
    assert (
        final_registers[1] != initial_registers[1]
    ), "Register 1 should be modified by sbrk"

    # Verify heap break was increased by ra (1024 bytes)
    expected_new_break = initial_heap_break + 1024
    assert (
        final_memory.heap_break == expected_new_break
    ), f"Heap break should be {expected_new_break}, got {final_memory.heap_break}"

    # Verify rd contains the new heap break value
    assert (
        final_registers[1] == expected_new_break
    ), f"Register 1 should contain {expected_new_break}, got {final_registers[1]}"


def test_sbrk_interpreter_zero_allocation():
    """Test sbrk instruction with zero allocation (just return current heap break)."""
    program = create_sbrk_test_program(rd=3, ra=4)

    # ra=4 contains 0 (no allocation)
    initial_registers = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    initial_memory = INT_Memory({}, [], [])
    initial_heap_break = initial_memory.heap_break

    status, pc, gas_left, final_registers, final_memory = Interpreter.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )

    print(f"Zero allocation - Status: {status}, Final registers: {final_registers}")

    # rd should contain the new heap break (should equal initial since allocation is 0)
    assert (
        final_registers[3] == initial_heap_break
    ), f"Register 3 should contain {initial_heap_break}, got {final_registers[3]}"
    # heap break should remain unchanged
    assert (
        final_memory.heap_break == initial_heap_break
    ), f"Heap break should remain {initial_heap_break}, got {final_memory.heap_break}"


def test_sbrk_interpreter_large_allocation():
    """Test sbrk instruction with large allocation."""
    program = create_sbrk_test_program(rd=0, ra=5)

    # ra=5 contains 65536 bytes (64KB)
    large_allocation = 65536
    initial_registers = [0, 0, 0, 0, 0, large_allocation, 0, 0, 0, 0, 0, 0, 0]
    initial_memory = INT_Memory({}, [], [])
    initial_heap_break = initial_memory.heap_break

    status, pc, gas_left, final_registers, final_memory = Interpreter.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )

    print(f"Large allocation - Status: {status}, Final registers: {final_registers}")

    # rd should contain the new heap break
    expected_new_break = initial_heap_break + large_allocation
    assert (
        final_registers[0] == expected_new_break
    ), f"Register 0 should contain {expected_new_break}, got {final_registers[0]}"
    # heap break should be increased by large_allocation
    assert (
        final_memory.heap_break == expected_new_break
    ), f"Heap break should be {expected_new_break}, got {final_memory.heap_break}"


def test_sbrk_interpreter_same_register():
    """Test sbrk instruction where rd == ra (edge case)."""
    program = create_sbrk_test_program(rd=2, ra=2)

    # ra=2 and rd=2, so register 2 contains allocation size and will receive result
    allocation_size = 512
    initial_registers = [0, 0, allocation_size, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    initial_memory = INT_Memory({}, [], [])
    initial_heap_break = initial_memory.heap_break

    status, pc, gas_left, final_registers, final_memory = Interpreter.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )

    print(f"Same register - Status: {status}, Final registers: {final_registers}")

    # rd should contain the new heap break (overwrites the original allocation size)
    expected_new_break = initial_heap_break + allocation_size
    assert (
        final_registers[2] == expected_new_break
    ), f"Register 2 should contain {expected_new_break}, got {final_registers[2]}"
    # heap break should be increased
    assert (
        final_memory.heap_break == expected_new_break
    ), f"Heap break should be {expected_new_break}, got {final_memory.heap_break}"


def test_sbrk_recompiler_basic():
    """Test sbrk instruction with recompiler - basic allocation."""
    # Create program and encode it for recompiler
    program = create_sbrk_test_program(rd=1, ra=2)
    buffer = bytearray(program.encode_size())
    program.encode_into(buffer)
    recomp_program = REC_Program.decode(bytes(buffer))

    # Initial registers: ra=2 contains 1024 (bytes to allocate)
    initial_registers = [0, 0, 1024, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    # Create guest memory
    guest_memory = REC_Memory.from_initial(
        [], [], VMContext.calculate_size(len(recomp_program.jump_table))
    )
    # Execute with recompiler
    result, pc, gas_left, final_registers, recom_mem = Recompiler.execute(
        recomp_program, 0, 1000, initial_registers.copy(), guest_memory
    )

    # The recompiler should execute the sbrk syscall
    # Register 1 should be modified to contain the new heap break
    assert final_registers[1] != initial_registers[1]
    assert final_registers[1] > 0  # Should contain some heap break value


def test_sbrk_consistency():
    """Test that interpreter and recompiler produce similar behavior."""
    # Test with interpreter
    program = create_sbrk_test_program(rd=1, ra=2)
    initial_registers = [0, 0, 1024, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    initial_memory = INT_Memory({}, [], [])

    interp_status, interp_pc, interp_gas, interp_regs, interp_mem = Interpreter.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )

    # Test with recompiler
    buffer = bytearray(program.encode_size())
    program.encode_into(buffer)
    recomp_program = REC_Program.decode(bytes(buffer))
    guest_memory = REC_Memory.from_initial(
        [], [], VMContext.calculate_size(len(recomp_program.jump_table))
    )

    recomp_result, recomp_pc, recomp_gas, recomp_regs, recom_mem = Recompiler.execute(
        recomp_program, 0, 1000, initial_registers.copy(), guest_memory
    )

    print(
        f"Consistency test - Interpreter: {interp_regs[1]}, Recompiler: {recomp_regs[1]}"
    )

    # Register values should show sbrk was executed
    # At minimum, the rd register should be non-zero in both cases
    assert (
        interp_regs[1] > 0
    ), f"Interpreter register 1 should be > 0, got {interp_regs[1]}"
    assert (
        recomp_regs[1] > 0
    ), f"Recompiler register 1 should be > 0, got {recomp_regs[1]}"

    # Both should have modified the same register
    assert (
        interp_regs[1] != initial_registers[1]
    ), "Interpreter should modify register 1"
    assert recomp_regs[1] != initial_registers[1], "Recompiler should modify register 1"
