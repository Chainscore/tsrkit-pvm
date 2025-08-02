# Tessera PVM

Tessera PVM is a Python implementation of the Tessera virtual machine, offering two execution modes: a straightforward interpreter and a more performant recompiler.

## Project Structure

-   `tsrkit_pvm/`: The main package.
    -   `core/`: Abstract base classes and core PVM components.
    -   `common/`: Shared utilities and data structures.
    -   `interpreter/`: The interpreter-based PVM implementation.
    -   `recompiler/`: The recompiler-based PVM implementation.
-   `tests/`: The project's test suite, which includes PVM test cases and schemas.

## Core Components

The fundamental building blocks of the PVM are defined in `tsrkit_pvm/core/`:

-   `ipvm.py`: Contains the `PVM` abstract base class.
-   `program_base.py`: Defines the base class for PVM programs.
-   `memory.py`: Provides the base class for memory management.

## Implementations

1.  **Interpreter**: Located in `tsrkit_pvm/interpreter/`, this implementation executes bytecode instruction by instruction. It is easier to debug and inspect.
2.  **Recompiler**: Found in `tsrkit_pvm/recompiler/`, this implementation recompiles PVM bytecode into native machine code for significantly faster execution.

## Installation

Install the package using pip:

```bash
pip install .
```

## Usage

The primary way to run a PVM program is to use the static `execute` method on either the `Interpreter` or `Recompiler` class.

Here is a corrected example of how to execute a PVM program with the interpreter:

```python
from tsrkit_pvm.interpreter.pvm import Interpreter
from tsrkit_pvm.interpreter.program import Program
from tsrkit_pvm.interpreter.memory import INT_Memory
from tsrkit_pvm.common.status import ExecutionStatus

# Your PVM bytecode
bytecode = bytes([0, 0, 14, 40, 2, 200, 50, 1, 40, 2, 200, 67, 2, 51, 1, 40, 246, 165, 20])

# 1. Decode the bytecode into a Program object
# The `decode` method returns a single Program instance.
program = Program.decode(bytecode)

# 2. Initialize memory, registers, and gas
# INT_Memory takes a dictionary for initial memory, a list for input, and a list for output.
memory = INT_Memory({}, [], [])
registers = [0] * 13  # PVM has 13 registers
gas = 100_000

# 3. Execute the program
status, final_pc, remaining_gas, final_registers, final_memory = Interpreter.execute(
    program=program,
    program_counter=0,
    gas=gas,
    registers=registers,
    memory=memory
)

# 4. Check the result
if status == ExecutionStatus.OUT_OF_GAS:
    print("Execution finished: Out of gas.")
    print(f"Gas consumed: {gas - remaining_gas}")
else:
    print(f"Execution finished with status: {status}")

```

## Testing

To run the comprehensive test suite and verify the functionality of both the interpreter and recompiler, use `pytest`:

```bash
poetry run pytest
```
