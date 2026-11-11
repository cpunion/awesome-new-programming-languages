# Allocation and reuse mechanism checks

These checks distinguish allocator calls, constructor creation, and compiler reuse from execution speed or whole-process memory use. [Results](results.json) support the [comparative study](../../research/memory-models.md).

Validated on macOS/ARM64 with Clang 22.1.8, Goose `f4637bf`, Lean 4.34.1, and Koka 3.2.9. The source revisions and binary identities are separate where applicable:

- Goose source: `f4637bfb342fb70d42bea0474eab9e62a3c99d68`; runtime identity `d521138194f1`.
- Lean reports commit `5045d0056413266e57c625dcd7c365b10e377c52`.
- Koka release tag `v3.2.9`: `facb7932ce6871fdb063f762a304bd8238f35fba`. The macOS ARM64 release archive SHA-256 is `b71fe2237b5f6b11116e296497b9756136a6d2a2514dcbf022aa9f620f04c088`.

Install/extract Koka in an isolated prefix and select an installed Lean toolchain explicitly. From this repository:

```sh
python3 experiments/memory-models-2026-11-11/run.py \
  --goose-bin /absolute/path/to/goose \
  --koka-bin /absolute/path/to/koka \
  --lean-toolchain leanprover/lean4:v4.34.1
```

The script uses a temporary directory and does not edit upstream sources. Native compilation/link flags were validated on macOS; other platforms need adaptation. This is not a timing benchmark, so the runs are not performance samples.

## Record storage

Each implementation builds 10,000 records with an ID and the name `row-ID`, then reads every name byte and computes checksum `56010610`. Goose emits standalone C; a forced-include header rewrites direct malloc/calloc/realloc/free/mmap calls in that translation unit. C controls use the same wrappers. Wrapper internals call the original C library functions.

The marked work made zero malloc calls for Goose, 10,001 for individual C allocations, and one for a manually packed C region. Goose startup made one malloc, two calloc calls, and two mmap calls reserving about 4 GiB of virtual address space. Those mappings are not a measurement of resident RAM. C requested-byte totals also describe capacity and allocation strategy, not a peak-memory ranking.

The instrumentation does not intercept allocations inside libc or other separately compiled libraries. It counts source-level requests, not logical bump-pointer allocations, physical page commitment, or process-wide allocation. Goose scope reclamation occurs after the work marker; the C controls explicitly free before it. Free counts therefore do not establish a uniform teardown comparison. No speed or RSS claim follows from these counters.

## Lean constructor reuse

The program transforms 1,000 small natural numbers by adding one, with a pure recursive list function. A generated-C header counts explicit `lean_alloc_ctor` call sites in that translation unit. It does not count constructor calls nested inside previously included headers or precompiled libraries. Small natural values in this input are immediate; the compared allocation sites create list nodes.

An external observer keeps the original list alive in the shared case and verifies its checksum, avoiding an accidental last-use optimization. Unique input made zero counted constructor calls; shared input made 1,000. Both transformed checksums are 500500, and the shared original remains 499500. The generated function in results.json shows the uniqueness check and constructor-reuse branch.

The C observer is trusted measurement code. This verifies a particular generated-code behavior; it is not a compiler soundness proof or a process-wide zero-allocation claim.

## Koka reuse and allocation contracts

The same pure list program builds with ordinary reuse and with `--fno-reuse`. Both print `501500`, `501500`, `500500`. The saved generated functions show a reuse token passed to the constructor in one variant, and a null token in the other. No Koka allocation counter or timing ratio was collected.

Two more probes check the compiler's treatment of `fip`. Reversal using consumed list cells builds and runs. A fresh constructor declared as an allocation-free `fip` function produces the diagnostic that it allocates at most one cell, **but the build still exits successfully** and the program runs. Results preserve that warning. This observation is important when distinguishing the FP² calculus's theorem from enforcement in this compiler's default command-line behavior.
