# Gojo

English | [简体中文](gojo.zh-CN.md)

Gojo is an experimental systems language built around ownership, restricted borrowing, deterministic cleanup, and structured concurrency. It combines a Rust implementation of the compiler with a C backend and a POSIX runtime. Its proposed appeal is safe native tools and services with a small language and quick builds. [Official repository](https://github.com/egoist/gojo)

## Research snapshot

Research date is 2026-11-11. This study pins commit `215e07c8f016203c52a68e91db9d7097e8e4ff4b`, dated 2026-11-10. The locally built compiler reports `gojo 0.0.1 (215e07c8f0, aarch64-apple-darwin)`. The language reference describes implemented behavior, while the packages and WebAssembly documents contain proposals as well. [Pinned source](https://github.com/egoist/gojo/tree/215e07c8f016203c52a68e91db9d7097e8e4ff4b), [language reference](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md), [WebAssembly proposal](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/wasm.md)

## Program correctness

Owned values move into `sink` parameters. Ordinary parameters borrow, and `inout` parameters require an explicit `&` at the call. The checker tracks moved and maybe-moved values, including loop-carried moves, mutable access conflicts, and views of values that may be modified. References and views have restricted storage and escape rules. A returned view can name its source with `of`, or the compiler can derive that provenance from returns. This reduces lifetime syntax by restricting the shapes of borrowing programs. [Ownership checker](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/src/borrowck.rs), [ownership rules](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#5-ownership)

Optionals use `?T`, errors use `T ! E`, and matches must cover their inputs. `linear struct` and `linear enum` require values to be consumed along every normal exit path, which can encode transaction commit/rollback protocols. Panics abort the process, so cleanup guarantees must be interpreted with that failure model. [Linear types](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#57-linear-types), [error handling](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#8-error-handling)

Release builds retain overflow, index, conversion, division, and unwrap checks. `requires` conditions are checked when a function is called and supply facts within its body. `checkfree fn` requires the compiler to eliminate every bounds check in that function. `gojo claims` exposes removed and retained checks. These are specific program analyses and contracts whose scope can be inspected in generated code and reports. [Bounds analysis](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/src/codegen/bce.rs), [execution rules](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#14-execution-model)

Raw-pointer dereferences, foreign calls, and unsafe functions require explicit unsafe blocks. Manifest policies can restrict unsafe dependencies and standard-library authority such as filesystem or network access. These checks depend on the language's standard-library boundary and the declared unsafe interfaces. [FFI and unsafe rules](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#11-unsafe-and-ffi), [manifest policies](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#21-package-manifest-gojotoml)

The project's assurance work includes regression cases, fuzzing, sanitizer runs, and adversarial borrowing programs. The pinned tree contains 259 compile-error fixtures and 257 adversarial checker fixtures. We ran the upstream `compile_errors` and `unsafe_programs_rejected` harness tests successfully, covering those 516 inputs. The current study also records 15 selected executable probes. Full sanitizer and long-running fuzzing campaigns remain outside this run. [Upstream harness](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/tests/suite.rs), [local probe results](../experiments/gojo-2026-11-11/results.json)

## Memory safety and efficiency

Values with observable cleanup, including files and user-defined destructors, are destroyed at scope exit. The compiler can free values earlier when destruction only releases memory and its analysis finds their last use. Borrow dependencies extend that use. Captures, defers, unsafe access, raw-pointer expressions, and types with observable cleanup constrain the optimization. [Drop analysis](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/src/codegen/drops.rs), [early-free design](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/drops.md)

`Vec` and `String` buffers use malloc/realloc. Small boxes and selected shared/interface allocations use thread-local size-class free lists. A consumed box can sometimes be reused for a replacement node. Sharing through Rc/Arc is explicit, and arenas use generational handles. Cyclic shared structures still need an appropriate weak-reference or arena design. [Runtime allocation and representation](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/runtime/gojo_rt.c), [box reuse and allocation rules](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#14-execution-model)

The project reports a two-phase allocation example dropping peak RSS from 383 MB to 192 MB through early frees. This is a project measurement on Apple M5, with a workload specifically suited to last-use reclamation. Our local loop provides little evidence about allocation behavior or peak memory. [Project memory measurements](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/drops.md#measurements)

## Systems programming

Gojo exposes fixed-width scalars through u64/i64 and f64, owned buffers and borrowed slices, raw pointers, and C-compatible foreign signatures. Foreign libraries can be linked statically or loaded through dlopen. Exported C functions have restrictions on callbacks and calling threads. Programs compile through a host C compiler, with Zig used for supported cross-compilation paths. [Numeric types](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#41-built-in-types), [C interoperability](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#11-unsafe-and-ffi)

The standard library includes files, processes, TCP/UDP/DNS, HTTP/TLS, serialization, and application utilities. Current native targets are macOS and Linux on arm64 and x86-64. The runtime relies on POSIX and a task scheduler. Windows, a package registry/version resolver, separate package compilation, and parts of tooling remain development gaps. WebAssembly is described in a proposal document. [Standard library index](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/std/README.md), [current project limitations](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/README.md#not-yet-implemented), [WebAssembly status](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/wasm.md)

Our assessment is that the implemented surface is well aligned with native command-line tools and services. Kernel, driver, embedded, and tightly controlled allocation/layout requirements need additional target and API evidence before making a systems-language selection.

## Concurrency model

`go` creates stackful tasks inside a `scope`, which waits for its children. Tasks can borrow data that outlives their scope, including disjoint slice regions. The compiler derives `send` capabilities and tracks task captures, mutable access, and escaping scope values. Mutex, RwLock, atomics, and channels provide shared-state mechanisms. Lock regions restrict operations that may wait. [Scopes and tasks](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#10-concurrency), [borrow checker](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/src/borrowck.rs)

The runtime schedules tasks M:N across workers, uses preemption checkpoints and blocking-call handling, and parks waiting I/O. Cancellation propagates through the task tree and interrupts supported blocking operations. Cleanup methods run shielded. A simulated scheduler with seeds, virtual time, interleaving exploration, and fault injection supports concurrent tests. Deadlock reporting and simulation provide diagnostics, with coverage determined by the explored workloads and schedules. [Scheduler implementation](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/runtime/gojo_sched.c), [runtime and simulation rules](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#107-runtime)

Stacks retain fixed addresses because tasks may borrow from each other's stacks. The runtime can hibernate sufficiently long-parked stacks, while pointers passed to C can pin them. The project reports 100,000 suspended tasks using 441 MB and 0.38 s on Linux, against Go's 284 MB and 0.11 s. An idle macOS workload benefits from stack hibernation. These published results make task lifetime and parking patterns essential to evaluating memory and scheduling costs. [Concurrency benchmarks and methodology](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/bench/README.md#goroutine)

## Metaprogramming

Generic functions and types are checked against capability constraints, then monomorphized. Integer const parameters express fixed dimensions. Structural interfaces support implicit satisfaction. Static reflection provides field/type iteration, static branches, and type-directed construction, enabling reusable serializers and decoders. Each facility has explicit rules for checking generic bodies and specialized code. [Generics and reflection](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#9-generics), [reflection implementation](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/src/check/body.rs)

The current design provides these bounded compile-time constructs. Arbitrary compile-time execution and a user macro system are outside the implemented metaprogramming surface described by the specification. Monomorphization and generated reflection code can increase C output and backend work, so large generic programs need separate compile-time and binary-size measurements.

## Local measurements

The experiment reuses the Bend study's C/Rust/Go/Zig xorshift32 sources and adds Gojo. Each implementation performs 50 million iterations from seed 1 and prints `376378803`. Measurements use Apple M4 Max, 16 cores, 128 GiB, macOS, clang 22.1.8, Rust 1.95.0-nightly, Go 1.27.3, and Zig 0.16.0. Gojo uses one scheduler worker. Five timed builds and seven timed runs follow one warmup each, in serial round-robin order. [Reproducible script](../experiments/gojo-2026-11-11/run.py), [raw results and toolchains](../experiments/gojo-2026-11-11/results.json)

| Implementation | Full build median | Execution median |
| --- | --- | --- |
| Gojo release | 171.7 ms | 76.16 ms |
| Go | 110.3 ms | 88.24 ms |
| Zig ReleaseFast | 103.6 ms | 75.86 ms |
| Rust opt-level=3 | 111.6 ms | 75.07 ms |
| C -O3 | 135.2 ms | 75.26 ms |

Gojo's runtime object is cached, and its generated-binary cache is cleared before each measured build. The first release build with a separate empty runtime cache took 2.021 s. Gojo uses clang -O2, with language checks retained. Other implementations use their recorded optimization settings and language defaults. Execution is about 1.012× C and 1.015× Rust here, with process startup and printing included. This workload primarily tests a scalar dependency chain. Allocation, contention, I/O, and large-project compilation remain separate questions.

Project benchmarks cover additional scalar, allocation, collection, and application workloads. Their Rust JSON/log comparison reports both faster and slower Gojo jobs, and its HTTP result also depends on the server libraries and load generation. Those results are project measurements on a different source version and hardware. [Microbenchmark methodology](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/bench/README.md), [application benchmark artifacts](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/bench/realworld/results/issue-4/after-pinned/RESULTS.md)

## Reproduction

The compiler build uses the pinned source and a separate target directory. The experiment also needs Python 3, clang, rustc, Go, Zig, and Git. Hardware collection currently uses macOS sysctl.

```sh
git clone https://github.com/egoist/gojo.git /tmp/gojo-research-source
git -C /tmp/gojo-research-source checkout 215e07c8f016203c52a68e91db9d7097e8e4ff4b
cargo build --release --locked --bin gojo \
  --manifest-path /tmp/gojo-research-source/Cargo.toml \
  --target-dir /tmp/gojo-research-target
python3 experiments/gojo-2026-11-11/run.py \
  --gojo-source /tmp/gojo-research-source \
  --gojo-bin /tmp/gojo-research-target/release/gojo \
  --output /tmp/gojo-research-results.json
```
