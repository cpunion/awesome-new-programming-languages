# Goose

English | [简体中文](goose.zh-CN.md)

[Goose](https://github.com/aardappel/goose) is Wouter van Oortmerssen's systems language built around compiler-managed data stacks, stable references, compact inline data, and isolated worker threads. It compiles whole programs to C and also provides an in-process TinyCC runner.

Reviewed on 2026-11-11 at commit [`f4637bfb342fb70d42bea0474eab9e62a3c99d68`](https://github.com/aardappel/goose/tree/f4637bfb342fb70d42bea0474eab9e62a3c99d68). The locally built compiler reports `goose f4637bf (runtime d521138194f1)`. The compiler is implemented in C++ and licensed under Apache-2.0. [Build definition](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/CMakeLists.txt)

## Correctness through roots and restrictions

References and slices have inferred roots describing the storage that keeps their targets alive. The checker rejects storing a reference where its root will die first, and prevents shrinking an array while a live reference may still point inside it. Multiple aliases are allowed; there is no Rust-style exclusive-borrow requirement or lifetime annotation syntax. Read-only contents use `const`; `let` alone restricts rebinding. [Lifetime rules](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#12-lifetimes-roots-stores-and-writability)

Bounds are checked unless proved safe, and `checkfree fn` makes eliminating the remaining checks an explicit compiler obligation. Unsigned arithmetic wraps; signed arithmetic wraps in release builds and is checked in debug builds. These are defined language choices, so memory safety does not imply arithmetic overflow rejection. Pool reuse can also produce a valid reference to a slot's next occupant, which remains a logical error the programmer must avoid. [Index types and checkfree](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#15-index-types-and-checkfree-functions) · [Arithmetic](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#3-scalars-and-arithmetic) · [Pools](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#14-reusable-pools)

No general proof that programs meet their specifications was established. The concrete contribution is a restrictive storage model enforced by a young compiler, supported by tests.

## Data stacks and compact representation

Dynamic values live on a compiler-selected set of data stacks backed by virtual address reservations. Growth advances a pointer; scope exit restores it. At most one resizable value occupies the top of each stack, so growing it does not move existing elements. This enables references to survive growth and permits constant-time storage reclamation for nested values. Flat nested data, variable-size enum variants, and narrow relative references can reduce padding, pointer overhead, and copying. [Memory model](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#4-where-values-live) · [Runtime implementation](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/src/runtime/runtime_impl.h)

This comes with constraints: recursive calls cannot retain arbitrary growable scratch data, variable-size element arrays need an additional reference index for random access, and long-lived mutation often requires explicit pools. The advertised absence of a heap allocator describes the language's data model. Runtime infrastructure still uses allocation, including thread and queue state, and reserving address space has operating-system costs. [Recursion](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#19-recursion) · [Thread runtime](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/src/runtime/runtime_threads.h)

## Systems programming and concurrency

Goose can emit C, build executables or shared libraries, call C through typed foreign declarations, and export functions with generated headers. Foreign code must respect the declared types and cannot retain borrowed arguments after the call. The data-stack model relies on virtual-memory support, so emitting portable C alone does not demonstrate suitability for a bare-metal target. Whole-program compilation, limited OS/library coverage, and the absence of runtime function pointers or escaping closures are practical constraints. [C interface](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#24-calling-c-and-being-called-from-c) · [Specification and open items](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/goose_spec.md#appendix-b-todo--open-items)

A `thread_fn` worker has its own data stacks and copies of the globals it uses. Arguments and typed-queue messages must be flat values with no references or slices inside. That prevents sharing mutable Goose storage between workers. The runtime implements the necessary copying, allocation, and synchronization internally; queues still permit blocking and deadlock. Workers have explicit spawn/wait operations, and contained workers can report an abort to their waiter. Threads require native builds because TinyCC cannot supply the required thread-local storage. [Thread model](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#22-threads)

## Metaprogramming

Generics specialize by type and inferred storage roots. Function values and trailing blocks are compile-time entities, enabling direct calls without runtime closure objects. `const for` expands over fields, enum variants, type lists, or compiler-known constants; `const if` selects fragments during specialization. This is useful structural reflection for serialization and generic transformations. The specification explicitly excludes arbitrary compile-time execution in this mechanism. Escaping closures and runtime function pointers remain unavailable. [Generics](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#18-generics-and-function-values) · [Expansion implementation](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/src/typecheck_expansion.h)

## Local experiments

[Script](../experiments/goose-2026-11-11/run.py) · [Results](../experiments/goose-2026-11-11/results.json) · [Upstream check log](../experiments/goose-2026-11-11/upstream-checks.txt)

All eight local probes matched expectations. Four compile-time rejections covered type mismatch, reference escape, shrinking with a live reference, and writing through `const`. Runtime bounds failure was detected. Positive programs preserved a reference through array growth, counted two struct fields by reflection, and showed a worker changing its own global to `7` while the parent's stayed `1`.

The upstream harness also passed with `--nocgen --no-jit -j4`, including 1,528 parse/roundtrip/type checks, 1,958 type-error cases, and 80 parse-error cases. This run intentionally skipped native C execution and TinyCC tests; the eight local probes provide separate native execution evidence. It was not a full sanitizer or graphics-suite run.

The 50-million-step UInt32 xorshift benchmark used an Apple M4 Max, 128 GiB RAM, five timed builds and seven timed executions after warmup. Builds ran serially in round-robin order with fresh source names; Goose's runtime object cache and the other toolchains were warm. Zig used a fresh local cache and incremental compilation was disabled. Every binary produced checksum `376378803`; execution includes startup and printing.

| Language | Build median | Execution median |
| --- | ---: | ---: |
| Goose f4637bf, `-O2`, Clang `-O2` | 0.21078 s | 0.07625 s |
| C / Clang 22.1.8, `-O3` | 0.13091 s | 0.07550 s |
| Rust 1.95.0-nightly, opt-level 3 | 0.10860 s | 0.07556 s |
| Go 1.27.3, defaults | 0.10907 s | 0.08926 s |
| Zig 0.16.0, ReleaseFast | 0.10296 s | 0.07705 s |

Here Goose's build took about 1.93 times Go and 2.05 times Zig, while execution was within about 1% of C and Rust. The first build with an empty Goose runtime-object cache took 0.7175 seconds. These measurements cover a small scalar program; they do not test the language's distinctive allocation, layout, or multicore advantages. TinyCC's unoptimized in-process runner was not used for these timings. [Build behavior](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/command_line.md#3-building-an-executable)

The upstream 16-workload suite reports separate C++ implementations, safe Rust comparisons, and memory measurements on Windows/AMD hardware, and includes workloads where Goose loses. Those are project measurements with different layouts and lifecycle costs, rather than local verification or a universal ranking. The dated benchmark report is more precise than the README's summary ratios. [Benchmark report](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/bench/results.md) · [Benchmark design](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/bench/design.md)

To reproduce, build the pinned source with CMake in Release mode, leaving optional builtin libraries empty, then run `python3 experiments/goose-2026-11-11/run.py --goose-bin /path/to/goose` with Clang, Rust, Go, and Zig installed. The script creates an isolated temporary `GOOSE_HOME`.
