# Awesome New Programming Languages

English | [简体中文](README.zh-CN.md)

A curated list of emerging programming languages and the ideas behind them.

We are especially interested in program correctness, memory safety and efficiency, systems programming, concurrency, and metaprogramming. Compilation speed is considered alongside Go and Zig, and execution performance alongside Rust and C. Linked research notes explore the implementation and available evidence.

## Contents

- [Systems Programming](#systems-programming)
- [Functional Programming and Proofs](#functional-programming-and-proofs)
- [Scientific and GPU Computing](#scientific-and-gpu-computing)
- [Domain-Specific Languages](#domain-specific-languages)
- [Upcoming Languages](#upcoming-languages)
- [Research and Experiments](#research-and-experiments)
- [Contributing](#contributing)

## Systems Programming

- [Gojo](https://github.com/egoist/gojo) — An experimental systems language with ownership, borrowing without lifetime parameters, deterministic cleanup, structured stackful tasks, and static reflection. Compiles to C. [Study](languages/gojo.md) · [中文](languages/gojo.zh-CN.md)
- [Goose](https://github.com/aardappel/goose) — A systems language using compiler-managed data stacks, inferred reference roots, compact inline values, isolated worker threads, and specialization-time reflection. Compiles to C. [Study](languages/goose.md) · [中文](languages/goose.zh-CN.md)
- [Rune](https://github.com/google/rune) — An unfinished systems language exploring secret-aware types, relational object ownership, Structure-of-Arrays storage, and compile-time code transformers. [Study](languages/rune.md) · [中文](languages/rune.zh-CN.md)

## Functional Programming and Proofs

- [Bend 2](https://github.com/bendlang/bend) — A pure language combining dependent types, affine ownership, explicit correctness proofs, compile-time templates, and fork-join execution on CPUs and GPUs. [Study (中文)](languages/bend.md)
- [Koka](https://github.com/koka-lang/koka) — An effect-typed functional language with compiler-inserted reference counting, uniqueness-based storage reuse, and fully in-place programming annotations. [Memory-model study](research/memory-models.md) · [中文](research/memory-models.zh-CN.md)
- [Zed](https://github.com/zedlanguage/zed) — A dataflow language under construction, with an implemented checking and memory-management core and plans for deterministic parallelism, proofs, and incremental collection processing. [Study](languages/zed.md) · [中文](languages/zed.zh-CN.md)

## Scientific and GPU Computing

- [Mojo](https://github.com/modular/modular/tree/main/Mojo) — A native language with Python-like syntax, ownership, compile-time specialization, SIMD, and explicit CPU/GPU programming. [Study](languages/mojo.md) · [中文](languages/mojo.zh-CN.md)

## Domain-Specific Languages

- [DIL](https://www.openui.com/blog/how-chatgpt-intelligent-ui-works) — A UI language described in a third-party reverse-engineering report, combining markup, component tags, and expressions for streamed interactive interfaces. [Research note](languages/dil.md) · [中文](languages/dil.zh-CN.md)

## Upcoming Languages

- [Blood](https://blood-lang.org/) — An announced language exploring types, effects, metaprogramming, and content-addressed code with semantic merging. Public implementation details and benchmarks are not yet available. [Research note](languages/blood.md) · [中文](languages/blood.zh-CN.md)

## Research and Experiments

- [Goose-style data stacks with a GC fallback](research/goose-hybrid-gc.md) — Workload coverage and measured precedents, automatic placement, cross-memory references, collection granularity, and performance-contract boundaries. [中文](research/goose-hybrid-gc.zh-CN.md)
- [Designs for independent lifetimes inside regions](research/region-reclamation-designs.md) — Reclaimable stores, declarative lifetime relationships, deferred deletion phases, and the boundary between safe reclamation and automatic graph collection. [中文](research/region-reclamation-designs.zh-CN.md)
- [How far can Goose's memory model go?](research/beyond-goose.md) — A design exploration of inferred regions, checked deletable handles, whole-region transfer, and scoped immutable sharing, with explicit costs and validation targets. [中文](research/beyond-goose.zh-CN.md)
- [Goose data-stack assignment checks](experiments/goose-stacks-2026-11-11/README.md) — Independent growth, reuse across scopes, result/scratch separation, and the distinction between last-use checks and owner reclamation. [Results](experiments/goose-stacks-2026-11-11/results.json)
- [Memory safety, fewer allocations, and less ownership bookkeeping](research/memory-models.md) — A comparative study of the collected languages, with Koka/Perceus and Lean as research references. [中文](research/memory-models.zh-CN.md) · [Allocation and reuse checks](experiments/memory-models-2026-11-11/README.md)
- [Bend behavior probes and integer-loop benchmark](experiments/bend-2026-11-11/run.py) — Reproducible checks and a C/Rust/Go/Zig comparison. [Results](experiments/bend-2026-11-11/results.json)
- [Gojo safety probes and integer-loop benchmark](experiments/gojo-2026-11-11/run.py) — Ownership and runtime checks, bounds-analysis reports, and a C/Rust/Go/Zig comparison. [Results](experiments/gojo-2026-11-11/results.json)
- [Mojo ownership probes and integer-loop benchmark](experiments/mojo-2026-11-11/run.py) — Compiler rejection checks, compile-time evaluation, and a C/Rust/Go/Zig comparison. [Results](experiments/mojo-2026-11-11/results.json)
- [Rune behavior probes](experiments/rune-2026-11-11/README.md) — Secret handling, runtime checks, generated relationships, and a documented secret-branch discrepancy. [Results](experiments/rune-2026-11-11/results.json)
- [Zed component checks and build observations](experiments/zed-2026-11-11/README.md) — Kernel bit-operation tests and current macOS build limitations. [Results](experiments/zed-2026-11-11/results.json)
- [Goose storage, thread, and reflection probes](experiments/goose-2026-11-11/run.py) — Native behavior checks, an upstream checker run, and a C/Rust/Go/Zig integer-loop comparison. [Results](experiments/goose-2026-11-11/results.json)

Research notes record source versions, primary references, limitations, and measurement conditions. Performance findings retain their workload and toolchain scope.

## Contributing

Suggestions, corrections, and new language introductions are welcome through issues and pull requests. Include a project link, a concise description, and sources for claims about language design or performance.
