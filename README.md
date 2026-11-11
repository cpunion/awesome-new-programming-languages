# Awesome New Programming Languages

English | [简体中文](README.zh-CN.md)

A curated list of emerging programming languages and the ideas behind them.

We are especially interested in program correctness, memory safety and efficiency, systems programming, concurrency, and metaprogramming. Compilation speed is considered alongside Go and Zig, and execution performance alongside Rust and C. Linked research notes explore the implementation and available evidence.

## Contents

- [Systems Programming](#systems-programming)
- [Scientific and GPU Computing](#scientific-and-gpu-computing)
- [Functional Programming and Proofs](#functional-programming-and-proofs)
- [Domain-Specific Languages](#domain-specific-languages)
- [Upcoming Languages](#upcoming-languages)
- [Research and Experiments](#research-and-experiments)
- [Contributing](#contributing)

## Systems Programming

- [Gojo](https://github.com/egoist/gojo) — An experimental systems language with ownership, borrowing without lifetime parameters, deterministic cleanup, structured stackful tasks, and static reflection. Compiles to C. [Study](languages/gojo.md) · [中文](languages/gojo.zh-CN.md)

## Functional Programming and Proofs

- [Bend 2](https://github.com/bendlang/bend) — A pure language combining dependent types, affine ownership, explicit correctness proofs, compile-time templates, and fork-join execution on CPUs and GPUs. [Study (中文)](languages/bend.md)

## Scientific and GPU Computing

- [Mojo](https://github.com/modular/modular/tree/main/Mojo) — A native language with Python-like syntax, ownership, compile-time specialization, SIMD, and explicit CPU/GPU programming. [Study](languages/mojo.md) · [中文](languages/mojo.zh-CN.md)

## Domain-Specific Languages

- [DIL](https://www.openui.com/blog/how-chatgpt-intelligent-ui-works) — A UI language described in a third-party reverse-engineering report, combining markup, component tags, and expressions for streamed interactive interfaces. [Research note](languages/dil.md) · [中文](languages/dil.zh-CN.md)

## Upcoming Languages

- [Blood](https://blood-lang.org/) — An announced language exploring types, effects, metaprogramming, and content-addressed code with semantic merging. Public implementation details and benchmarks are not yet available. [Research note](languages/blood.md) · [中文](languages/blood.zh-CN.md)

## Research and Experiments

- [Bend behavior probes and integer-loop benchmark](experiments/bend-2026-11-11/run.py) — Reproducible checks and a C/Rust/Go/Zig comparison. [Results](experiments/bend-2026-11-11/results.json)
- [Gojo safety probes and integer-loop benchmark](experiments/gojo-2026-11-11/run.py) — Ownership and runtime checks, bounds-analysis reports, and a C/Rust/Go/Zig comparison. [Results](experiments/gojo-2026-11-11/results.json)
- [Mojo ownership probes and integer-loop benchmark](experiments/mojo-2026-11-11/run.py) — Compiler rejection checks, compile-time evaluation, and a C/Rust/Go/Zig comparison. [Results](experiments/mojo-2026-11-11/results.json)

Research notes record source versions, primary references, limitations, and measurement conditions. Performance findings retain their workload and toolchain scope.

## Contributing

Suggestions, corrections, and new language introductions are welcome through issues and pull requests. Include a project link, a concise description, and sources for claims about language design or performance.
