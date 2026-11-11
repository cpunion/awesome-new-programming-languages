# Zed

English | [简体中文](zed.zh-CN.md)

[Zed](https://github.com/zedlanguage/zed) is Luke Hutchison's dataflow language centered on immutable definitions and multi-level maps. It aims to combine collection processing, incremental computation, compiler checks, and automatic parallelism. This is the programming language hosted at `zedlanguage/zed`.

Reviewed on 2026-11-11 at commit [`4598c420ab65fba1942f12a0888bc9f638fba9f9`](https://github.com/zedlanguage/zed/tree/4598c420ab65fba1942f12a0888bc9f638fba9f9). **The project is under construction. Its README explicitly describes the finished language**, while the implementation status and source record a smaller working core. The repository uses the MIT license. [README](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/README.md) · [Implementation status](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/STATUS.md)

## Correctness as a language design goal

The design treats failures as values in result unions, describes static range/refinement checks, and requires explicit handling of missing lookups and ambiguous collection merges. This is attractive for data transformations: changing a map's keys can introduce collisions that deserve an explicit policy, and filtering failed rows can change an aggregate's meaning. These are examples of the intended semantics, rather than a claim that every README example works in the current implementation. [Worked example and checks](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/README.md#checks-at-compile-time)

The source and progress record include a checker, type refinement, Presburger reasoning, staging, a reference evaluator, ZIR lowering, and differential tests. The proposed `law` facility distinguishes proof or exhaustive checking from sampled tests, with only proved laws usable as optimizer rewrites. That broader proof story still needs implementation evidence: at this snapshot, `zed-cert/src/lib.rs` contains only a five-line module comment describing a future independent checker. A crate name is insufficient evidence that rewrite certificates are checked today. [Checker source](https://github.com/zedlanguage/zed/tree/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zedc-check/src) · [Certificate crate](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zed-cert/src/lib.rs)

## Memory management

There is concrete implementation beyond the design prose. The ZIR memory planner infers borrowing and inserts reference-count duplication and drops at last use, with fusion for destructuring. Its checking machine verifies counts after operations. The native runtime represents a value with a tag and payload, leaves common scalars unboxed, and uses a counted heap for other values. Freed cells advance a generation, allowing stale-cell access to be detected. This is a useful basis for researching the cost of automatic memory management. [Memory planner](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zedc-zir/src/zir/memory.rs) · [Runtime heap](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zed-rt/src/heap.rs)

The completed-language design goes further: elimination of intermediate collections, in-place updates when unique, bounded allocation assertions, and amortized freeing. Those goals should be evaluated separately from the current scalar/tuple/closure memory plan. No allocation or resident-memory benchmark was completed in this study.

## Concurrency, systems support, and metaprogramming

The design derives parallel work from dependencies and promises deterministic outputs, including floating-point reductions, with explicit exceptions for external events and certain operations. **The current runtime source says work stealing and the wave scheduler come at later layers.** It therefore does not establish a usable implementation of the full automatic multicore model. [Runtime scope](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zed-rt/src/lib.rs)

The current native code path uses Cranelift and links a Rust runtime. MLIR/LLVM, GPUs, distributed execution, hardware synthesis, and microcontrollers are future targets in the project layout and plan. C import/export, foreign memory layouts, and bounded-allocation annotations are described in the language design; this study did not validate them end to end. Systems suitability consequently remains a research question. [Native backend](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zed-native/src/lib.rs) · [Repository layout](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/docs/layout.md)

Metaprogramming is intended to use ordinary evaluation at build time, partial evaluation, structural reflection, function source as data, and compilation of generated code. Grammar-based parsing/serialization and symbolic algebra are prominent examples in the design. The repository contains staging machinery; that alone does not verify the full reflection, grammar, or proof-carrying rewriting feature set. [Staging source](https://github.com/zedlanguage/zed/tree/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zedc-stage/src)

## Local checks and performance limits

[Reproduction notes](../experiments/zed-2026-11-11/README.md) · [Recorded results](../experiments/zed-2026-11-11/results.json)

The unmodified native compiler failed to build on macOS/ARM64 with the installed Rust 1.99 toolchain: the runtime uses Linux APIs including `sysinfo` and `MAP_STACK`. An interpreter-only harness calling the `zedc` library also failed because package discovery uses `OFlags::PATH`. These observations identify portability limitations of this snapshot; they do not establish a failure on Linux. [Stack source](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zed-rt/src/stack.rs) · [Package discovery](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zedc/src/place.rs)

Three upstream kernel bit-operation tests did run and pass on macOS, checking agreement between machine and exact arithmetic paths and rejection of out-of-domain operands. This validates a small component, with no successful end-to-end language run or performance comparison.

There are consequently no Go/Zig build-speed or Rust/C execution ratios to report. The current native backend deliberately defaults to Cranelift's `opt_level=none` and a single-pass register allocator to control compilation cost, leaving the stronger ZIR optimizer for later work. Future comparisons should measure that tradeoff explicitly, alongside collection workloads, allocation, and deterministic multicore scaling.
