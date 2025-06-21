# Tessera Polkadot Virtual Machine (PVM)

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A high-performance PVM implementation for the Tessera client, featuring both an interpreter and recompiler for optimal bytecode execution.

## Overview

Tessera PVM implementation is designed to execute bytecode efficiently with support for both Interpreter and Recompiler modes.

## Architecture

The PVM consists of two main methodologies:

### 1. Interpreter (`tsrkit_pvm.interpreter`)

The interpreter provides the core execution engine with:

- **PVM**: Main virtual machine class for bytecode execution
- **Program**: Program blob handling and instruction management
- **Memory**: Memory management with paging and access control
- **Instructions**: Complete instruction set implementation
- **Status**: Execution status and error handling
- **Register**: Register file management

### 2. Recompiler (`tsrkit_pvm.recompiler`)

WIP

## Installation

### From PyPI (when published)

```bash
pip install tsrkit-pvm
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/tessera-project/tsr-pvm.git
cd tsr-pvm

# Install in development mode
pip install -e ".[dev]"
```

## Quick Start

```python
from tsrkit_pvm import PVM, Program, Memory

# Create a simple program
program_data = b"..."  # Your bytecode here
program = Program.from_json(program_data)

# Initialize memory
memory = Memory()

# Create and run PVM
pvm = PVM(program, memory)
status = pvm.run()

print(f"Execution completed with status: {status}")
```

## Dependencies

- **Python**: 3.11 or higher
- **tsrkit-types**: Type definitions and utilities for the TSR Kit ecosystem

## Development

### Setting up Development Environment

```bash
# Clone the repository
git clone https://github.com/tessera-project/tsr-pvm.git
cd tsr-pvm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tsrkit_pvm --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests
```

### Code Quality

The project uses several tools to maintain code quality:

```bash
# Format code
black tsrkit_pvm/
isort tsrkit_pvm/

# Lint code
flake8 tsrkit_pvm/

# Type checking
mypy tsrkit_pvm/
```

### Project Structure

```
tsr-pvm/
├── tsrkit_pvm/                 # Main package
│   ├── __init__.py            # Package exports
│   ├── interpreter/           # Interpreter submodule
│   │   ├── __init__.py       # Interpreter exports
│   │   ├── pvm.py            # Main PVM class
│   │   ├── program.py        # Program handling
│   │   ├── memory.py         # Memory management
│   │   ├── status.py         # Status and errors
│   │   ├── register.py       # Register management
│   │   ├── constants.py      # PVM constants
│   │   └── instructions/     # Instruction set
│   │       ├── __init__.py
│   │       ├── inst_map.py   # Instruction mapping
│   │       ├── opcode.py     # Opcode definitions
│   │       └── tables/       # Instruction tables
│   └── recompiler/           # Recompiler submodule (planned)
│       └── __init__.py       # Recompiler exports
├── tests/                    # Test suite
├── pyproject.toml           # Project configuration
├── README.md               # This file
└── .gitignore             # Git ignore rules
```

## API Reference

### Core Classes

#### PVM

The main virtual machine class for executing bytecode.

```python
from tsrkit_pvm import PVM

pvm = PVM(program, memory)
status = pvm.run()
```

#### Program

Handles program blob loading and instruction management.

```python
from tsrkit_pvm import Program

# Load from bytecode
program = Program.from_json(bytecode_data)

# Access program properties
print(f"Jump table: {program.jump_table}")
print(f"Instruction set size: {len(program.instruction_set)}")
```

#### Memory

Manages virtual machine memory with paging support.

```python
from tsrkit_pvm import Memory

memory = Memory()
memory.write(address, data)
data = memory.read(address, size)
```

### Status Codes

The PVM uses several status codes to indicate execution state:

- `CONTINUE`: Normal execution continues
- `HALT`: Execution completed successfully
- `PANIC`: Fatal error occurred
- `OUT_OF_GAS`: Execution limit reached
- `PAGE_FAULT`: Memory access violation
- `HOST`: Host function call required

## Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Run code quality checks (`black`, `isort`, `flake8`, `mypy`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting
- Add type hints for all public APIs
- Write comprehensive docstrings
- Maintain test coverage above 90%

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.

## Support

- **Issues**: [GitHub Issues](https://github.com/tessera-project/tsr-pvm/issues)
- **Documentation**: [Read the Docs](https://tsr-pvm.readthedocs.io)
- **Discussions**: [GitHub Discussions](https://github.com/tessera-project/tsr-pvm/discussions)

## Acknowledgments

- Tessera Team
- Polkadot ecosystem contributors