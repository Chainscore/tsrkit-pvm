### PVM Benchmarking [Draft 1]
#### Interpreter vs Recompiler vs EVM L1

---

This benchmark evaluates execution performance of JAM's Polkadot Virtual Machine (PVM) using two modes: an interpreter and an ahead-of-time (AOT) recompiler. All tests were performed on Tessera, a clean-room Python implementation of the PVM developed by ChainScore Labs. Benchmarks include synthetic (ADD_JUMP) and real-world (Conway's Game of Life) workloads.

---

### ADD\_JUMP Benchmark

| Mode            | Time (ms) | Gas/us  | Speedup (vs Interpreter - Time) | Speedup (vs Interpreter - Gas/us) |
| --------------- | --------- | ------- | ------------------------------- | --------------------------------- |
| PVM Recompiler x86_64  | 0.83      | 1207.94 | \~2869x                         | \~2876x                           |
| EVM L1          | N/A       | 1.25    | N/A                             | \~2.98x                           |
| PVM Interpreter | 2382.36   | 0.42    | 1x                              | 1x                                |

* Gas consumed: 1_000_000
* Assembly time: 0.02776 us/instruction

---

### Conway's Game of Life (CGOL) Benchmark

| Mode            | Time (ms) | Gas/us | Speedup (vs Interpreter - Time) | Speedup (vs Interpreter - Gas/us) |
| --------------- | --------- | ------ | ------------------------------- | --------------------------------- |
| PVM Recompiler x86_64 | 1.68      | 593.54 | \~3267x                         | \~3297x                           |
| EVM L1          | N/A       | 1.25   | N/A                             | \~6.94x                           |
| PVM Interpreter | 5487.54   | 0.18   | 1x                              | 1x                                |

* Gas consumed: 1_000_000
* Assembly time: 0.18869 us/instruction

---

### Summary

| Benchmark | Assembly Time (us/inst) | PVM Recompiler Gas/us | EVM L1 Gas/us | Recompiler vs EVM | EVM vs Interpreter |
| --------- | ----------------------- | --------------------- | ------------- | ----------------- | ------------------ |
| ADD\_JUMP | 0.02776                 | 1207.94               | 1.25          | \~966.35x         | \~2.98x            |
| CGOL      | 0.18869                 | 593.54                | 1.25          | \~474.83x         | \~6.94x            |

---

### Environment

* Architecture: x86\_64
* VM Spec:

  * 13 general-purpose registers
  * 4GB linear memory
* Interpreter and Recompiler executed with identical PVM instruction set (as defined in JAM Graypaper §20)
* Recompiler uses AOT translation of PVM RISC-V instructions

---

* EVM baseline: 1.25M gas/sec = **1.25 gas/us** (reth, 2024)
* PVM Recompiler delivers 3–4 orders of magnitude gains over interpreter
* Recompiled execution exceeds EVM throughput by 2–3 orders of magnitude
* Assembly cost per instruction remains < 0.2 us
