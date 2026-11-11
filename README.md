# Awesome New Programming Languages

English | [简体中文](README.zh-CN.md)

Introductions and research on emerging programming languages, with a focus on program correctness, memory safety and efficiency, systems programming, and compilation and execution performance.

Each study examines a language's design and use cases through official documentation, source code, and reproducible experiments. We record current capabilities, limitations, and supporting evidence, using Go and Zig as compilation benchmarks and Rust and C as execution benchmarks. Detailed language studies are currently written in Chinese.

## Research Focus

| Area | Questions |
| --- | --- |
| Program correctness | Which errors does the type system prevent? Which application properties can be expressed and verified? What assumptions and escape hatches affect those guarantees? |
| Memory safety and efficiency | How does the language handle ownership, aliasing, lifetimes, array access, concurrent access, and resource cleanup? What are the costs of allocation, reclamation, copying, layout, and peak memory usage? |
| Systems programming | What support exists for data representation, numeric types, FFI, OS interfaces, concurrency, resource control, native libraries, and target platforms? |
| Compilation and execution performance | How does the development experience compare with Go and Zig, and execution performance with Rust and C, on relevant workloads? |

## Language Index

Bend 2 combines dependent types, affine ownership, and explicit correctness proofs with CPU/GPU execution. It is the first language studied here. The detailed study covers its design and the four research areas above. [Official project](https://github.com/bendlang/bend) · [Bend 2 study (Chinese)](languages/bend.md)

| Language | Snapshot | Correctness | Memory | Systems programming | Performance |
| --- | --- | --- | --- | --- | --- |
| [Bend 2](languages/bend.md) | 2026-11-11, source version 2.0.40 | Dependent and affine types, explicit laws and proofs, and a Lean verification kernel | Ownership and selective reference counting in native builds, in-place array updates, wrapping indices | File, network, process, and C/JS effect interfaces, with limited low-level control and native library output | The local integer loop performs close to C/Rust, with longer full native builds than the Go/Zig implementations |

## Evidence and Comparisons

Studies record the research date and a pinned source commit, citing official documentation, implementations, tests, and papers. Project claims, source analysis, local measurements, and inferences are identified in context.

Performance records include toolchains, hardware, optimization flags, cache state, repetitions, and raw results. Comparisons account for the following factors.

- Compilation measurements cover checking and proofs, code generation, backend optimization, linking, cold builds, and incremental edits.
- Execution measurements cover single-core, multicore, and GPU runs, including startup and warmup costs.
- Data representation, algorithms, inputs, output validation, and hardware resources determine comparability.
- Peak RSS, live heap size, total allocation, and GPU-resident memory capture different costs.
- Microbenchmark conclusions retain their workload scope. Large-project behavior requires measurements at the corresponding scale.

## Experiments

- [Bend behavior probes and five-language integer loop](experiments/bend-2026-11-11/run.py)
- [Raw measurements and diagnostics](experiments/bend-2026-11-11/results.json)

Reproduction instructions are included in the detailed study. [Bend experiment instructions (Chinese)](languages/bend.md#实验复现)

## Contributing

Use issues to suggest languages, share primary sources, or flag changes to existing findings. Pull requests can add language introductions, improve studies, and contribute reproducible experiments. New studies can follow the four research areas above and record their research date, source version, and references.
