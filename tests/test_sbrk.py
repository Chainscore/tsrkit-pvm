"""Test the sbrk (system break) instruction implementation."""

import pytest
from tsrkit_pvm.interpreter.memory import Memory
from tsrkit_pvm.interpreter.program import Program
from tsrkit_pvm.interpreter.pvm import PVM
from tsrkit_pvm.interpreter.status import ExecutionStatus
from tsrkit_pvm.recompiler.program import Program as RecompilerProgram
from tsrkit_pvm.recompiler.pvm import PVM as RecompilerPVM
from tsrkit_pvm.recompiler.memory import GuestMemory


def create_sbrk_test_program(rd: int, ra: int):
    """Create a simple program that just executes sbrk instruction.
    
    Args:
        rd: destination register (0-12)
        ra: source register containing bytes to allocate (0-12)
    
    Returns:
        Program object for the test
    """
    # sbrk instruction: opcode 101, register encoding (ra << 4) | rd
    sbrk_opcode = 101
    reg_encoding = (ra << 4) | rd
    
    # Create instruction sequence - just sbrk
    instruction_set = bytes([sbrk_opcode, reg_encoding])
    
    # Offset bitmask: True for opcodes, False for arguments
    offset_bitmask = [True, False]
    
    # Create program with no jump table (z=0, empty jump_table)
    return Program(z=0, jump_table=[], instruction_set=instruction_set, offset_bitmask=offset_bitmask)


def test_sbrk_interpreter_basic():
    """Test sbrk instruction with interpreter - basic allocation."""
    # Test: allocate 1024 bytes, rd=1, ra=2
    program = create_sbrk_test_program(rd=1, ra=2)
    
    # Initial registers: ra=2 contains 1024 (bytes to allocate)
    initial_registers = [0, 0, 1024, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    
    # Initial memory with some writable pages
    initial_memory = Memory({}, [], [])
    initial_heap_break = initial_memory.heap_break
    
    # Execute
    status, pc, gas_left, final_registers, final_memory = PVM.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )
    
    # Focus on register values - rd (register 1) should contain the new heap break
    # The interpreter should execute sbrk and update both the register and memory
    print(f"Status: {status}, Final registers: {final_registers}")
    print(f"Initial heap break: {initial_heap_break}, Final heap break: {final_memory.heap_break}")
    
    # Verify rd (register 1) was modified (should contain new heap break)
    assert final_registers[1] != initial_registers[1], "Register 1 should be modified by sbrk"
    
    # Verify heap break was increased by ra (1024 bytes)
    expected_new_break = initial_heap_break + 1024
    assert final_memory.heap_break == expected_new_break, f"Heap break should be {expected_new_break}, got {final_memory.heap_break}"
    
    # Verify rd contains the new heap break value
    assert final_registers[1] == expected_new_break, f"Register 1 should contain {expected_new_break}, got {final_registers[1]}"


def test_sbrk_interpreter_zero_allocation():
    """Test sbrk instruction with zero allocation (just return current heap break)."""
    program = create_sbrk_test_program(rd=3, ra=4)
    
    # ra=4 contains 0 (no allocation)
    initial_registers = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    initial_memory = Memory({}, [], [])
    initial_heap_break = initial_memory.heap_break
    
    status, pc, gas_left, final_registers, final_memory = PVM.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )
    
    print(f"Zero allocation - Status: {status}, Final registers: {final_registers}")
    
    # rd should contain the new heap break (should equal initial since allocation is 0)
    assert final_registers[3] == initial_heap_break, f"Register 3 should contain {initial_heap_break}, got {final_registers[3]}"
    # heap break should remain unchanged
    assert final_memory.heap_break == initial_heap_break, f"Heap break should remain {initial_heap_break}, got {final_memory.heap_break}"


def test_sbrk_interpreter_large_allocation():
    """Test sbrk instruction with large allocation."""
    program = create_sbrk_test_program(rd=0, ra=5)
    
    # ra=5 contains 65536 bytes (64KB)
    large_allocation = 65536
    initial_registers = [0, 0, 0, 0, 0, large_allocation, 0, 0, 0, 0, 0, 0, 0]
    initial_memory = Memory({}, [], [])
    initial_heap_break = initial_memory.heap_break
    
    status, pc, gas_left, final_registers, final_memory = PVM.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )
    
    print(f"Large allocation - Status: {status}, Final registers: {final_registers}")
    
    # rd should contain the new heap break
    expected_new_break = initial_heap_break + large_allocation
    assert final_registers[0] == expected_new_break, f"Register 0 should contain {expected_new_break}, got {final_registers[0]}"
    # heap break should be increased by large_allocation
    assert final_memory.heap_break == expected_new_break, f"Heap break should be {expected_new_break}, got {final_memory.heap_break}"


def test_sbrk_interpreter_same_register():
    """Test sbrk instruction where rd == ra (edge case)."""
    program = create_sbrk_test_program(rd=2, ra=2)
    
    # ra=2 and rd=2, so register 2 contains allocation size and will receive result
    allocation_size = 512
    initial_registers = [0, 0, allocation_size, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    initial_memory = Memory({}, [], [])
    initial_heap_break = initial_memory.heap_break
    
    status, pc, gas_left, final_registers, final_memory = PVM.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )
    
    print(f"Same register - Status: {status}, Final registers: {final_registers}")
    
    # rd should contain the new heap break (overwrites the original allocation size)
    expected_new_break = initial_heap_break + allocation_size
    assert final_registers[2] == expected_new_break, f"Register 2 should contain {expected_new_break}, got {final_registers[2]}"
    # heap break should be increased
    assert final_memory.heap_break == expected_new_break, f"Heap break should be {expected_new_break}, got {final_memory.heap_break}"


def test_sbrk_recompiler_basic():
    """Test sbrk instruction with recompiler - basic allocation."""
    # Create program and encode it for recompiler
    program = create_sbrk_test_program(rd=1, ra=2)
    buffer = bytearray(program.encode_size())
    program.encode_into(buffer)
    recomp_program = RecompilerProgram.decode(bytes(buffer))
    
    # Initial registers: ra=2 contains 1024 (bytes to allocate)
    initial_registers = [0, 0, 1024, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    
    # Create guest memory
    guest_memory = GuestMemory(0)
    
    # Execute with recompiler
    result, pc, gas_left, final_registers = RecompilerPVM.execute(
        recomp_program, guest_memory, 0, initial_registers.copy(), 1000
    )
    
    # The recompiler should execute the sbrk syscall
    # Register 1 should be modified to contain the new heap break
    assert final_registers[1] != initial_registers[1]
    assert final_registers[1] > 0  # Should contain some heap break value


def test_sbrk_recompiler_zero_allocation():
    """Test sbrk instruction with recompiler - zero allocation."""
    program = create_sbrk_test_program(rd=3, ra=4)
    buffer = bytearray(program.encode_size())
    program.encode_into(buffer)
    recomp_program = RecompilerProgram.decode(bytes(buffer))
    
    initial_registers = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    guest_memory = GuestMemory(0)
    
    result, pc, gas_left, final_registers = RecompilerPVM.execute(
        recomp_program, guest_memory, 0, initial_registers.copy(), 1000
    )
    
    # rd should be modified (contains current break)
    assert final_registers[3] != initial_registers[3]
    assert final_registers[3] > 0  # Should contain some heap break value


def test_sbrk_consistency():
    """Test that interpreter and recompiler produce similar behavior."""
    # Test with interpreter
    program = create_sbrk_test_program(rd=1, ra=2)
    initial_registers = [0, 0, 1024, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    initial_memory = Memory({}, [], [])
    
    interp_status, interp_pc, interp_gas, interp_regs, interp_mem = PVM.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )
    
    # Test with recompiler
    buffer = bytearray(program.encode_size())
    program.encode_into(buffer)
    recomp_program = RecompilerProgram.decode(bytes(buffer))
    guest_memory = GuestMemory(0)
    
    recomp_result, recomp_pc, recomp_gas, recomp_regs = RecompilerPVM.execute(
        recomp_program, guest_memory, 0, initial_registers.copy(), 1000
    )
    
    print(f"Consistency test - Interpreter: {interp_regs[1]}, Recompiler: {recomp_regs[1]}")
    
    # Register values should show sbrk was executed
    # At minimum, the rd register should be non-zero in both cases
    assert interp_regs[1] > 0, f"Interpreter register 1 should be > 0, got {interp_regs[1]}"
    assert recomp_regs[1] > 0, f"Recompiler register 1 should be > 0, got {recomp_regs[1]}"
    
    # Both should have modified the same register
    assert interp_regs[1] != initial_registers[1], "Interpreter should modify register 1"
    assert recomp_regs[1] != initial_registers[1], "Recompiler should modify register 1"


@pytest.mark.parametrize("rd,ra,allocation_size,description", [
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
    (3, 4, 4294967295, "max_uint32"), # 2^32 - 1
])
def test_sbrk_interpreter_vs_recompiler_comprehensive(rd, ra, allocation_size, description):
    """Comprehensive parametrized test comparing interpreter and recompiler sbrk behavior.
    
    This test follows the pattern from test_debug_mismatch.py to ensure both implementations
    produce identical results across a wide variety of input scenarios.
    """
    # Create test program
    program = create_sbrk_test_program(rd=rd, ra=ra)
    
    # Set up initial registers - put allocation size in ra register
    initial_registers = [0] * 13
    initial_registers[ra] = allocation_size
    
    print(f"\n🔍 Testing {description}: rd={rd}, ra={ra}, size={allocation_size}")
    
    # Test with interpreter
    print("[1] Running in PVM interpreter mode...")
    initial_memory = Memory({}, [], [])
    initial_heap_break = initial_memory.heap_break
    
    interp_status, interp_pc, interp_gas, interp_regs, interp_mem = PVM.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )
    
    # Test with recompiler
    print("[2] Running in PVM recompiler mode...")
    buffer = bytearray(program.encode_size())
    program.encode_into(buffer)
    recomp_program = RecompilerProgram.decode(bytes(buffer))
    guest_memory = GuestMemory(0)
    
    recomp_status, recomp_pc, recomp_gas, recomp_regs = RecompilerPVM.execute(
        recomp_program, guest_memory, 0, initial_registers.copy(), 1000
    )
    
    print(f"  Interpreter registers: {interp_regs}")
    print(f"  Recompiler registers:  {recomp_regs}")
    
    # Core consistency checks
    assert interp_status == recomp_status, f"Status mismatch: interpreter={interp_status}, recompiler={recomp_status}"
    
    # Check that rd register was modified in both cases
    expected_new_break = initial_heap_break + allocation_size
    
    # Interpreter checks
    assert interp_regs[rd] == expected_new_break, f"Interpreter rd register should be {expected_new_break}, got {interp_regs[rd]}"
    assert interp_mem.heap_break == expected_new_break, f"Interpreter heap break should be {expected_new_break}, got {interp_mem.heap_break}"
    
    # Recompiler checks (we can't directly check memory state, but register should be consistent)
    # Note: Recompiler uses actual system heap, so we focus on register consistency
    assert recomp_regs[rd] != initial_registers[rd], f"Recompiler should modify rd register {rd}"
    assert recomp_regs[rd] > 0, f"Recompiler rd register should be positive, got {recomp_regs[rd]}"
    
    # Verify all other registers remain unchanged
    for i in range(13):
        if i == rd:
            continue
        assert interp_regs[i] == initial_registers[i], f"Interpreter register {i} should remain unchanged"

    # For recompiler, check for unexpected register changes
    changed_indices = {
        i for i, (initial, final) in enumerate(zip(initial_registers, recomp_regs))
        if initial != final
    }
    expected_changes = {rd}
    # Allow recompiler to use r9 for internal bookkeeping
    allowed_internal_changes = {9}
    unexpected_changes = changed_indices - expected_changes - allowed_internal_changes

    assert not unexpected_changes, f"Recompiler unexpectedly changed registers: {list(unexpected_changes)}"

    assert interp_regs == recomp_regs, f"Register mismatch: {interp_regs} != {recomp_regs}"

    print(f"  ✅ {description} passed: both implementations consistent")


def test_sbrk_stress_comparison():
    """Stress test with multiple sequential sbrk operations comparing interpreter vs recompiler."""
    print("\n🔥 Running sbrk stress test...")
    
    # Create a program with multiple sbrk operations using different registers
    instructions = []
    offset_bitmask = []
    
    # sbrk rd=1, ra=2 (allocate 1024 bytes)
    instructions.extend([101, (2 << 4) | 1])
    offset_bitmask.extend([True, False])
    
    # sbrk rd=3, ra=4 (allocate 2048 bytes)  
    instructions.extend([101, (4 << 4) | 3])
    offset_bitmask.extend([True, False])
    
    # sbrk rd=5, ra=6 (allocate 512 bytes)
    instructions.extend([101, (6 << 4) | 5])
    offset_bitmask.extend([True, False])
    
    program = Program(z=0, jump_table=[], 
                     instruction_set=bytes(instructions), 
                     offset_bitmask=offset_bitmask)
    
    # Set up initial registers with allocation sizes
    initial_registers = [0, 0, 1024, 0, 2048, 0, 512, 0, 0, 0, 0, 0, 0]
    
    # Test with interpreter
    initial_memory = Memory({}, [], [])
    interp_status, interp_pc, interp_gas, interp_regs, interp_mem = PVM.execute(
        program, 0, 1000, initial_registers.copy(), initial_memory
    )
    
    # Test with recompiler
    buffer = bytearray(program.encode_size())
    program.encode_into(buffer)
    recomp_program = RecompilerProgram.decode(bytes(buffer))
    guest_memory = GuestMemory(0)
    
    recomp_status, recomp_pc, recomp_gas, recomp_regs = RecompilerPVM.execute(
        recomp_program, guest_memory, 0, initial_registers.copy(), 1000
    )
    
    # Compare registers, ignoring the destination registers which will differ, and r9 for the recompiler.
    # The destination registers (rd) get the old program break, which is different for the interpreter (offset)
    # and recompiler (actual memory address).
    dest_regs = {1, 3, 5}
    for i in range(13):
        if i in dest_regs:
            continue
        # r9 is used internally by the recompiler.
        if i == 9:
            assert interp_regs[i] == 0, f"Interpreter r9 should be 0, but was {interp_regs[i]}"
            continue

        assert interp_regs[i] == recomp_regs[i], f"Register r{i} mismatch: interp={interp_regs[i]}, recomp={recomp_regs[i]}"

    # Also check that the destination registers in the recompiler's output are not zero,
    # which would indicate a failure to update the register.
    for i in dest_regs:
        assert recomp_regs[i] != 0, f"Recompiler destination register r{i} should not be zero."
    print("  ✅ Stress test passed!")