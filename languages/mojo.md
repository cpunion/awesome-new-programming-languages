# Mojo

English | [简体中文](mojo.zh-CN.md)

Mojo combines Python-like syntax with native value types, ownership, compile-time specialization, and CPU/GPU programming. Its strongest fit in this collection is performance-oriented libraries and heterogeneous computing. [Project](https://github.com/modular/modular/tree/f364f26cd29207a9501625f566527354bb5dac4f/Mojo) · [Manual](https://mojolang.org/docs/manual/)

Reviewed on 2026-11-11. The tested package reports **Mojo 1.2.0 (2016d0cd)**. The separately inspected public source snapshot is `f364f26cd29207a9501625f566527354bb5dac4f`; its identity is not established as the source of that binary. Mojo is now open source under Apache-2.0 with LLVM exceptions; MAX has separate licensing. [Source and licensing](https://github.com/modular/modular/tree/f364f26cd29207a9501625f566527354bb5dac4f)

## Ownership and correctness

Values have owners, function arguments are immutable by default, `mut` grants exclusive mutable access, and `^` explicitly transfers ownership. Origins track the lifetime and mutability of references, including pointers and spans. This provides useful compiler checks against mutable aliasing and using a transferred value. A function declared `raises` requires callers to handle or propagate its errors. These mechanisms establish local safety properties; they do not prove an algorithm meets its specification. [Ownership](https://mojolang.org/docs/manual/values/ownership/) · [Lifetimes](https://mojolang.org/docs/manual/values/lifetimes/) · [Errors](https://mojolang.org/docs/manual/errors/)

The safety boundary matters for systems code. Untracked origins and unsafe pointer operations give programmers responsibility for allocation, initialization, bounds, and lifetime. Ownership checking cannot make an incorrect unsafe implementation safe. Custom resource types must supply the appropriate destruction behavior. [Pointers](https://mojolang.org/docs/manual/pointers/using-pointers/)

## Memory and systems programming

Mojo normally destroys a value after its last use, using **ASAP destruction** rather than waiting for the end of its lexical scope. Borrowing can extend its lifetime. Code that relies on a resource remaining alive must account for that policy; explicitly destroyed types can require a deliberate destruction operation. This offers prompt cleanup without a tracing collector while retaining low-level allocation APIs. [Destruction](https://mojolang.org/docs/manual/lifecycle/death/) · [Explicit destruction](https://mojolang.org/docs/manual/lifecycle/explicit-destroy/)

The compiler supports native executables, object files, assembly, LLVM IR, shared libraries, and device targets. C interoperability and inline MLIR provide substantial low-level reach. Python interoperability helps reuse an existing ecosystem, but it does not imply arbitrary Python programs acquire native Mojo performance. Shared libraries using parallel APIs need the documented runtime initialization when hosted by C. [Compilation](https://mojolang.org/docs/tools/compilation/) · [Inline MLIR](https://mojolang.org/docs/reference/inline-mlir/)

## Concurrency and metaprogramming

CPU parallelism is available through library APIs such as `parallelize`, which dispatches indexed work and waits for completion. GPU programming uses explicit kernels and device contexts, with asynchronous transfers and launches followed by synchronization. The GPU APIs are supplied through MAX. This study did not establish a general compiler guarantee of race freedom for arbitrary parallel kernels, and did not run GPU experiments. [CPU parallelize](https://max.modular.com/api/mojo/max/algorithm/backend/cpu/parallelize/parallelize/) · [GPU tutorial](https://max.modular.com/gpu/intro-tutorial/)

Compile-time parameters, traits, evaluation, and reflection enable specialized containers and numerical kernels. Specialization can remove runtime dispatch and generic metadata work, while also creating more compiler work and code variants. Inline MLIR extends that control to compiler-level operations. [Metaprogramming](https://mojolang.org/docs/manual/metaprogramming/) · [Evaluation](https://mojolang.org/docs/manual/metaprogramming/comptime-evaluation/) · [Reflection](https://mojolang.org/docs/manual/metaprogramming/reflection/)

## Local experiments

[Script](../experiments/mojo-2026-11-11/run.py) · [Raw results](../experiments/mojo-2026-11-11/results.json)

Five negative probes were rejected with the expected diagnostics: a type mismatch, mutation through an immutable argument, two mutable arguments aliasing one list, use after ownership transfer, and an unhandled raising call. One positive probe evaluated `comptime N = 6 * 7` and printed `42`. All six matched expectations.

The benchmark executes the same 50-million-step UInt32 xorshift loop used in the other studies. All five languages produced checksum `376378803`. Measurements used an Apple M4 Max with 128 GiB RAM, native ARM64 binaries, five timed builds and seven timed executions after warmup, serialized in round-robin order. Toolchains and filesystem were warm; each build had a fresh source filename, and Zig had a fresh local cache with incremental compilation disabled. Execution includes process startup and printing.

| Language | Build median | Execution median |
| --- | ---: | ---: |
| Mojo 1.2.0, `-O3` | 1.0233 s | 0.08329 s |
| C / Clang 22.1.8, `-O3` | 0.1368 s | 0.07778 s |
| Rust 1.95.0-nightly, opt-level 3 | 0.1141 s | 0.07830 s |
| Go 1.27.3, defaults | 0.1107 s | 0.09186 s |
| Zig 0.16.0, ReleaseFast | 0.1049 s | 0.07853 s |

For this small CPU workload, Mojo executed within about 7% of C and 6% of Rust, while its build took about 9.2 times Go and 9.8 times Zig. This is evidence of competitive scalar code generation, with a larger fixed build cost here. It does not measure large projects, incremental builds, allocation behavior, SIMD, Python interoperability, or GPU throughput.

The installed compiler emitted a non-fatal Crashpad initialization warning; builds and executions succeeded. The raw results preserve that warning. Reproduce with an isolated installation following the [official installation guide](https://mojolang.org/install/), then run `python3 experiments/mojo-2026-11-11/run.py --mojo-bin /path/to/mojo` with the other four toolchains available.
