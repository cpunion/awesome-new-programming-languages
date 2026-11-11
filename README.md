# Awesome New Programming Languages

English | [简体中文](README.zh-CN.md)

Introductions and research on emerging programming languages, with a focus on program correctness, memory safety and efficiency, systems programming, compilation and execution performance, concurrency models, and metaprogramming.

Each study examines a language's design and use cases through official documentation, source code, and reproducible experiments. We record current capabilities, limitations, and supporting evidence, using Go and Zig as compilation benchmarks and Rust and C as execution benchmarks. Studies link to the available English and Chinese editions.

## Research Focus

| Area | Questions |
| --- | --- |
| Program correctness | Which errors does the type system prevent? Which application properties can be expressed and verified? What assumptions and escape hatches affect those guarantees? |
| Memory safety and efficiency | How does the language handle ownership, aliasing, lifetimes, array access, concurrent access, and resource cleanup? What are the costs of allocation, reclamation, copying, layout, and peak memory usage? |
| Systems programming | What support exists for data representation, numeric types, FFI, OS interfaces, concurrency, resource control, native libraries, and target platforms? |
| Compilation and execution performance | How does the development experience compare with Go and Zig, and execution performance with Rust and C, on relevant workloads? |
| Concurrency model | How are tasks scheduled and shared data checked? How do synchronization, cancellation, deadlocks, blocking I/O, and CPU/GPU execution work? |
| Metaprogramming | What support exists for generics, specialization, macros, reflection, compile-time evaluation, and code generation? What are their checking rules and compilation costs? |

## Language Index

Each study examines the six research areas above and records the source version and evidence behind its findings.

| Language | Main ideas | Current findings | Study |
| --- | --- | --- | --- |
| [Bend 2](https://github.com/bendlang/bend) | Dependent and affine types, explicit laws and proofs, CPU/GPU fork-join, compile-time templates | Native integer loop close to C/Rust. Full builds, scheduling balance, unsafe boundaries, and specialization costs need attention. Snapshot 2.0.40, 2026-11-11. | [中文](languages/bend.md) |
| [Gojo](https://github.com/egoist/gojo) | Ownership and restricted views, linear resources, structured M:N tasks, generics and static reflection | Native integer loop close to C/Rust. Warm runtime-cache builds are competitive at small scale. Prototype maturity, task stacks, and whole-program compilation remain relevant. Snapshot 0.0.1, 2026-11-11. | [English](languages/gojo.md) · [中文](languages/gojo.zh-CN.md) |

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
- [Bend raw measurements and diagnostics](experiments/bend-2026-11-11/results.json)
- [Gojo safety probes and five-language integer loop](experiments/gojo-2026-11-11/run.py)
- [Gojo raw measurements, diagnostics, and bounds claims](experiments/gojo-2026-11-11/results.json)

Reproduction instructions are included in the detailed study. [Bend experiment instructions (Chinese)](languages/bend.md#实验复现)

## Contributing

Use issues to suggest languages, share primary sources, or flag changes to existing findings. Pull requests can add language introductions, improve studies, and contribute reproducible experiments. New studies can follow the six research areas above and record their research date, source version, and references.
