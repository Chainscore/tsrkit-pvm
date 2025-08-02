import logging
import pytest
from tsrkit_pvm.interpreter.memory import INT_Memory
from tsrkit_pvm.interpreter.program import INT_Program
from tsrkit_pvm.interpreter.pvm import Interpreter
from tsrkit_pvm.common.status import ExecutionStatus
from tsrkit_pvm.recompiler.program import REC_Program
from tsrkit_pvm.recompiler.pvm import Recompiler
from tsrkit_pvm.recompiler.memory import REC_Memory

from tests.sbrk.utils import create_sbrk_test_program
from tsrkit_pvm.recompiler.vm_context import VMContext


logger = logging.getLogger("sbrk_compare")
logger.setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "rd,ra,allocation_size,description",
    [
        # Basic cases
        (1, 2, 0, "zero_allocation"),
        (1, 2, 1024, "basic_1kb"),
        (1, 2, 4096, "page_size_4kb"),
        (0, 1, 8192, "basic_8kb_rd0"),
        # Large allocations
        (3, 4, 65536, "large_64kb"),
        (5, 6, 1048576, "large_1mb"),
        (7, 8, 16777216, "very_large_16mb"),
        # Small allocations
        (2, 3, 1, "tiny_1byte"),
        (4, 5, 8, "small_8bytes"),
        (6, 7, 256, "small_256bytes"),
        # Edge cases with register combinations
        (0, 12, 2048, "min_max_regs"),
        (12, 0, 512, "max_min_regs"),
        (6, 6, 1024, "same_register"),
        # Power of 2 boundaries
        (1, 2, 128, "power2_128"),
        (1, 2, 2048, "power2_2048"),
        (1, 2, 32768, "power2_32kb"),
        # Odd sizes
        (2, 3, 1337, "odd_1337"),
        (4, 5, 12345, "odd_12345"),
        (8, 9, 987654, "odd_987654"),
        # Near boundary values (testing potential overflow handling)
        (1, 2, 2147483647, "max_int32"),  # 2^31 - 1
        (3, 4, 4294967295, "max_uint32"),  # 2^32 - 1
    ],
)
def test_sbrk_i_vs_native(rd, ra, allocation_size, description):
    """Parametrized test comparing interpreter and recompiler sbrk behavior."""
    # Create test program
    program = create_sbrk_test_program(rd=rd, ra=ra)

    # Set up initial registers - put allocation size in ra register
    initial_registers = [0] * 13
    initial_registers[ra] = allocation_size

    print(f"\n🔍 Testing {description}: rd={rd}, ra={ra}, size={allocation_size}")

    # Test with interpreter
    print("[1] Running in PVM interpreter mode...")
    # initial_memory = Memory.from_pc(b"", b"", b"args", 0, 0)
    initial_memory = INT_Memory({}, [], [])
    initial_heap_break = initial_memory.heap_break

    interp_status, interp_pc, interp_gas, interp_regs, interp_mem = Interpreter.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )

    # Test with recompiler
    print("[2] Running in PVM recompiler mode...")
    buffer = bytearray(program.encode_size())
    program.encode_into(buffer)
    recomp_program = REC_Program.decode(bytes(buffer))
    guest_memory = REC_Memory.from_initial(
        [], [], VMContext.calculate_size(len(recomp_program.jump_table))
    )

    recomp_status, recomp_pc, recomp_gas, recomp_regs, recom_mem = Recompiler.execute(
        recomp_program, 0, 1000, initial_registers.copy(), guest_memory, logger
    )

    print(f"  Interpreter registers: {interp_regs}")
    print(f"  Recompiler registers:  {recomp_regs}")

    # Core consistency checks
    assert (
        interp_status == recomp_status
    ), f"Status mismatch: interpreter={interp_status}, recompiler={recomp_status}"

    # Check that rd register was modified in both cases
    expected_new_break = initial_heap_break + allocation_size

    # Interpreter checks
    assert (
        interp_regs[rd] == expected_new_break
    ), f"Interpreter rd register should be {expected_new_break}, got {interp_regs[rd]}"
    assert (
        interp_mem.heap_break == expected_new_break
    ), f"Interpreter heap break should be {expected_new_break}, got {interp_mem.heap_break}"

    # Recompiler checks (we can't directly check memory state, but register should be consistent)
    # Note: Recompiler uses actual system heap, so we focus on register consistency
    if allocation_size > 0 and ra != rd:
        assert (
            recomp_regs[rd] != initial_registers[rd]
        ), f"Recompiler should modify rd register {rd}"
        assert (
            recomp_regs[rd] > 0
        ), f"Recompiler rd register should be positive, got {recomp_regs[rd]}"

    # Verify all other registers remain unchanged
    for i in range(13):
        if i == rd:
            continue
        assert (
            interp_regs[i] == initial_registers[i]
        ), f"Interpreter register {i} should remain unchanged"

    # For recompiler, check for unexpected register changes
    changed_indices = {
        i
        for i, (initial, final) in enumerate(zip(initial_registers, recomp_regs))
        if initial != final
    }
    expected_changes = {rd}
    # Allow recompiler to use r9 for internal bookkeeping
    allowed_internal_changes = {9}
    unexpected_changes = changed_indices - expected_changes - allowed_internal_changes

    assert (
        not unexpected_changes
    ), f"Recompiler unexpectedly changed registers: {list(unexpected_changes)}"

    assert (
        interp_regs == recomp_regs
    ), f"Register mismatch: {interp_regs} != {recomp_regs}"

    print(f"  ✅ {description} passed: both implementations consistent")
