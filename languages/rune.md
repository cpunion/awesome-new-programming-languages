# Rune

English | [简体中文](rune.zh-CN.md)

[Rune](https://github.com/google/rune) is an experimental systems language combining Python-inspired syntax, secret-aware types, declarative object relationships, and Structure-of-Arrays storage. It is particularly interesting as an alternative approach to managing complex object graphs. The repository explicitly says it is unfinished and is **not an officially supported Google product**. [Project status](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/README.md)

Reviewed on 2026-11-11 at commit `a8fb12f974736f20eaefb1f614df68411dac7bc8`, under Apache-2.0. The implementation studied here is the C compiler emitting LLVM IR and invoking Clang. Documents about the Rune-written bootstrap compiler and proposed transformer upgrades describe additional future work. [Compiler driver](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/src/main.c) · [Bootstrap proposal](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/compiler_phases.md)

## Correctness and secret data

Rune infers types, has explicitly nullable types, and enables bounds, overflow, and destroyed-object checks by default. Its `-U` mode disables important runtime protections. These checks address particular invalid operations; there is no demonstrated general proof of program correctness. [Language reference](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#memory-safety)

The distinguishing security idea is secret propagation: results derived from `secret` values retain secrecy, and selected operations use constant-time implementations. The reference says secrets cannot control branches or indices. However, that statement exceeds what our local probes established: secret indexing was rejected, while the following **runtime-input-dependent secret branch compiled successfully** with default safety and `-O`:

```text
password = secret(argv[1])
if password == "password" {
  println "leaked"
}
```

Running it with argument `password` printed `leaked`. The recorded LLVM IR contains the secret comparison and a conditional branch to the output block. The current binding code checks an `if` condition's Boolean type without rejecting its secrecy, and code generation emits an ordinary conditional branch. This is a reproducible mismatch with the documented restriction; it is not a measurement of a complete timing attack. [Binding code](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/bind/bindexpr.c#L1982) · [Branch generation](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/llvm/genllvm.c#L3963) · [Probe results](../experiments/rune-2026-11-11/results.json)

The upstream TODO also lists optimizer-safe secret struct comparison, secret select handling, and further constant-time tests. Its reference defines constant time relative to equal-length inputs and excludes other side channels. Secret types are therefore an interesting design direction with important implementation gaps at this revision. [Secret semantics](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#constant-time-processing-of-secrets) · [TODO](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/TODO)

## Relational memory management

Classes participate in declared relationships such as doubly linked lists or one-to-one associations. A cascade relation makes destroying a parent destroy its children; generated cleanup also updates the other participating objects. Classes outside cascade ownership use reference counting. The reference describes static analysis and restrictions on reference loops as further parts of the safety design. This shifts significant bookkeeping from individual pointer operations to the declared data model. [Memory model and relations](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#relations)

Fields are stored in separate arrays, with object references represented as indices. Scanning a few fields can avoid loading unrelated fields and can use smaller references. The benefit depends on the access pattern; it does not establish universal superiority over C/Rust layouts or allocators. Whole-object access, allocation growth, and destruction of large graphs need separate measurement. The TODO still includes improvements to destruction safety and memory pools, so the documentation's broad memory-safety claims should be read alongside those gaps. [Data model](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/database_design.md) · [Memory-management implementation](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/transformer/memmanage.c)

## Systems programming, concurrency, and metaprogramming

The compiler analyzes an entire program or standalone library, emits LLVM IR, and links native code through Clang. C-compatible library boundaries are part of its model. Rich C++ interoperability, C pointer support, memory-mapped I/O declarations, and other low-level facilities remain listed as work to do; the aspiration to replace C++ is broader than the implemented interface surface. [Compilation units](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#compilation-units) · [Systems TODOs](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/TODO)

The project explicitly lacks multithreading support at this snapshot. Iterators and relationship traversal do not establish an actor model, structured task system, or data-race guarantee. Concurrent systems programming is a substantial missing area.

Metaprogramming is a core strength of the approach: compile-time interpreted transformers generate or modify class fields, methods, and cleanup. The bundled `DoublyLinked` transformer is executable evidence, and the local relationship probe exercised its generated insertion and removal. The proposal to compile transformers into dynamically loaded HIR-manipulating libraries is a separate future design. [Current transformer](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/builtin/doublylinked.rn) · [Transformer reference](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#transformers) · [Upgrade proposal](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/transformers.md)

## Local checks and performance evidence

[Reproduction instructions](../experiments/rune-2026-11-11/README.md) · [Script](../experiments/rune-2026-11-11/run.py) · [Results](../experiments/rune-2026-11-11/results.json)

The unmodified compiler built in an Ubuntu 24.04 x86-64 container with Clang 14, DataDraw, GMP, and CTTK. Five of six probe expectations held: secret indexing and type changes were rejected; overflow and out-of-bounds access stopped at runtime; generated relationship methods inserted an item, removed it on destruction, and cleared the parent's link. The sixth probe exposed the accepted secret branch above. Array-bounds failure printed a panic and exited with status 139; overflow exited with status 1. These are observed behaviors, with no claim that the whole upstream suite passed.

The host is Apple Silicon, while this container is x86-64. No performance ratio against native macOS Go/Zig/Rust/C is reported. A useful future comparison should run all toolchains on the same native Linux machine and include both safe defaults and explicitly identified unsafe configurations. Tiny programs would measure fixed compiler/linker cost; object-graph workloads would exercise the layout and destruction design.

Upstream contains binary-tree and priority-queue examples, with varying C++ allocation strategies. Their results cannot establish a general language ranking, and the repository's own queue report describes differing outcomes across workloads. There is no verified Go/Zig compilation comparison in this study. [Benchmark sources](https://github.com/google/rune/tree/a8fb12f974736f20eaefb1f614df68411dac7bc8/benchmarks) · [Upstream observations](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/benchmarks/results.md)
