# Memory safety, fewer allocations, and less ownership bookkeeping

English | [简体中文](memory-models.zh-CN.md)

Reviewed on 2026-11-11. **These three goals can coexist for useful classes of programs.** Compiler-inserted reference counting with reuse, and inferred region allocation, provide concrete examples. The evidence does not establish that any language reviewed here gives arbitrary mutable object graphs, prompt reclamation, unrestricted sharing, and the best allocation behavior simultaneously without costs or restrictions.

The useful distinction is who manages ownership: a compiler may track it internally while ordinary programs contain no ownership annotations or explicit transfers. This is a legitimate improvement. The absence of an ownership checker alone does not establish automatic lifetime safety.

## What the evidence means

Memory safety here concerns bounds, initialization, type-correct access, and lifetime validity in the language's safe fragment. It does not automatically include freedom from leaks, stale application identities, data races, or resource leaks. Runtime and foreign-code correctness remain relevant. A proof about a calculus is distinct from a proof about its deployed compiler and runtime.

Allocation has several separate measures: logical objects created, allocator requests, requested bytes, reserved virtual address space, peak live data, and resident memory. Fewer `malloc` calls can result from pooling while the same amount of data remains live. Earlier destruction can reduce peak live data without reducing allocation count. Our earlier integer loops did not measure these properties.

“No GC” also needs a definition. The comparison below distinguishes tracing collection from automatic reference counting. Reference counting has bookkeeping and reclamation costs even when the source program never manages ownership.

## The strongest established route: automatic counting and reuse

Perceus, published at PLDI 2021 and implemented in Koka, automatically inserts precise reference-count operations and enables reuse of matching constructor storage when it is unique. The authors provide formal results for a specified core calculus; the garbage-free result has a cycle-free premise. Subsequent work on frame-limited reuse addresses retention costs caused by reuse decisions. This is a documented research contribution, rather than a recent language's unverified speed claim. [Perceus paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2020/11/perceus-tr-v4.pdf) · [Frame-limited reuse](https://www.microsoft.com/en-us/research/publication/reference-counting-with-frame-limited-reuse-extended-version/)

Koka's functional source can describe a fresh list while the implementation rewrites unique nodes in place. Shared input needs preservation, so the same operation may allocate. The paper does not provide a universal solution to cyclic mutable graphs or all concurrency costs. Its formal claims should not be generalized to zero allocation or a fully verified compiler. [Koka reuse](https://koka-lang.github.io/koka/doc/book.html#why-fbip)

The later FP² work (ICFP 2023) goes further: a restricted linear calculus supports checked fully in-place functions, with stated no-allocation and constant-stack properties under its premises. Koka supplies `fip`/`fbip` annotations. These add useful algorithm-level contracts, with restrictions and uniqueness requirements; they do not promise a shared caller never copies. Our Koka 3.2.9 probe accepted a valid `fip` reversal, but an allocating function incorrectly declared `fip` produced a warning and still built. The tested compiler's default exit status therefore cannot alone certify that a declared allocation contract holds. [FP² paper](https://www.microsoft.com/en-us/research/uploads/prod/2023/05/fbip.pdf)

Koka's manual still identifies it as a research language with library and package-management gaps. The allocation research does not establish its suitability as a general replacement for Rust/C systems code. This study measured no new Go/Zig compilation or Rust/C execution comparisons for Koka or Lean. [Project scope](https://koka-lang.github.io/koka/doc/book.html#getstarted)

Lean independently provides a practical example of automatic reference counting, constructor reuse, and copy-on-write primitives. Ordinary functional code can reuse storage without a programmer writing ownership transfers. Sharing changes the cost. [Lean runtime reference](https://lean-lang.org/doc/reference/latest/Run-Time-Code/Reference-Counting/)

Inferred regions are also established prior art: Tofte and Talpin's region-based memory work predates these projects and was implemented in ML Kit. This establishes a lineage, not that Goose implements their exact algorithm. Assessing Goose's novelty requires examining its particular combination of stable references, inline variable-size representation, destinations, and restrictions. [Region-based memory management, 1997](https://www.sciencedirect.com/science/article/pii/S0890540196926139)

## New local checks

[Sources and reproduction](../experiments/memory-models-2026-11-11/README.md) · [Results](../experiments/memory-models-2026-11-11/results.json)

- **Goose records:** 10,000 records contain generated variable-length names. The workload reads every name byte. Instrumented generated C made zero `malloc`/`calloc`/`realloc` calls during the marked work. Startup did allocate runtime metadata and reserve two virtual mappings. Zero work-phase calls therefore does not mean zero memory use or allocation by the OS.
- **C controls:** a per-record allocation implementation made 10,001 `malloc` calls; a manually packed region implementation made one. All three produced the same checksum. The control shows that Goose automates a useful layout/allocation strategy; it does not give Goose an allocation capability unavailable to C.
- **Lean reuse:** the same pure list transformation over 1,000 small natural numbers made zero new list-constructor calls at the instrumented generated-C sites when the input was unique, and 1,000 when the original was retained. Both results had checksum 500500; the retained original kept checksum 499500. The counter excludes allocations in precompiled libraries and header helpers.
- **Koka 3.2.9:** reuse enabled/disabled produced identical outputs, including preservation of shared input. Enabled code passes reusable storage into the list constructor; disabled code passes the null reuse token. This is code-generation evidence, with no Koka allocation count or speed ratio claimed.
- **Koka allocation contracts:** a valid `fip` reversal ran successfully. A `fip` function creating a fresh list cell without reuse credit was diagnosed as allocating, yet also built and ran under default settings. The distinction between a diagnostic and a rejecting guarantee matters.

These checks demonstrate mechanisms. They do not prove memory safety, rank total memory consumption, or measure long-lived services, cyclic graphs, concurrency, and resident-memory behavior.

## Assessment of the languages already collected

### Goose: substantial allocation automation within a restricted storage model

At tested revision `f4637bf`, inferred roots and liveness checks protect references; compiler-assigned data stacks, destination construction, and inline nested values avoid per-object allocation. The newer reviewed head `32a4f445d8a94b22874a28469f95f69ba3ac31dd` adds unrelated features; the relevant model is unchanged. This is a valuable engineering integration with direct local evidence. There is no evidence here of a new general theorem eliminating memory-management tradeoffs. [Memory model](https://github.com/aardappel/goose/blob/32a4f445d8a94b22874a28469f95f69ba3ac31dd/docs/reference.md#4-where-values-live)

Programmers still choose owners, scopes, pools, and representation. Recursive growable locals, compact variable-size indexing, and escaping function values are restricted. Pool reuse does not automatically invalidate old object identities. This meets the goal well for suitable data pipelines and regional workloads, while leaving work in long-lived mutable graphs. [Limitations and pools](https://github.com/aardappel/goose/blob/32a4f445d8a94b22874a28469f95f69ba3ac31dd/docs/tutorial.md#18-limitations)

### Gojo and Mojo: simpler ownership expression with useful compiler assistance

Gojo `215e07c` retains explicit borrowing, `inout`, `sink`, and shared `Rc`/`Arc` choices. Last-use reclamation for eligible memory-only values lowers retention; small-object allocation and some box reuse address different costs. These are useful implementation improvements, with continued programmer participation in ownership. [Gojo drops](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/drops.md) · [Execution model](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#14-execution-model)

Mojo 1.2.0 uses ownership, origins, mutable access conventions, and explicit transfers. ASAP destruction can reduce retention; value representation and specialization can avoid some allocation. These mechanisms do not automatically remove ownership decisions or guarantee fewer heap requests. Untracked origins and unsafe operations carry additional obligations. [Ownership](https://mojolang.org/docs/manual/values/ownership/) · [Lifetimes](https://mojolang.org/docs/manual/values/lifetimes/) · [Destruction](https://mojolang.org/docs/manual/lifecycle/death/)

### Bend 2: meaningful language theory with explicit affine constraints

At `d18110b`, affine consumption and selective sharing guide native reclamation. Arrays have flat specialized representations and support in-place updates; other values still occupy a runtime heap. The source programmer observes affine use and explicit duplication rules. Its type-theory proofs are significant evidence about the stated calculus, with a separate trusted boundary around translation, code generation, runtime, and unsafe features. It addresses correctness and efficient execution together, without satisfying a strict requirement for ownership-transparent general systems code. [Runtime ownership](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ) · [Study](../languages/bend.md)

### Rune: relational ownership can automate graph bookkeeping

At `a8fb12f`, declared relationships generate linking and cleanup; cascade ownership avoids some reference counts, and SoA field arrays amortize object storage. Programmers design the relationships instead of managing every pointer. This is an interesting combination building on DataDraw-style ideas. It does not establish universally lower allocation for variable-size fields, or a complete memory-safety guarantee for the unfinished implementation. Its secret-branch discrepancy is a separate security finding and does not by itself refute the memory model. [Reference](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#memory-safety) · [Open work](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/TODO)

### Zed: promising automatic planning, incomplete broad claims

The checked `4598c42` source has an actual ZIR memory planner, inferred borrowing, last-use drops, and a counted runtime. At newer reviewed head `63662d8d7f1646ff6230275f1f270dae9747de2a`, those files are unchanged. Full collection fusion, broad target support, and the complete verification story still require evidence. The certificate crate remains a module comment. The local macOS build limitation prevented an end-to-end memory experiment, so its intended combination cannot yet be treated as demonstrated. [Memory planner](https://github.com/zedlanguage/zed/blob/63662d8d7f1646ff6230275f1f270dae9747de2a/crates/zedc-zir/src/zir/memory.rs) · [Certificate crate](https://github.com/zedlanguage/zed/blob/63662d8d7f1646ff6230275f1f270dae9747de2a/crates/zed-cert/src/lib.rs)

### Zig, Odin, C3, Blood, and DIL

Zig, Odin, and C3 make explicit allocation, arenas, temporary regions, and cleanup more convenient. They remain manual-memory systems: ordinary programmer responsibility for lifetime does not disappear with a region helper or `defer`. Their general pointer models therefore do not meet the complete automatic-safety requirement. This assessment is documentation-based; no new memory experiment was run for them. [Zig lifetime responsibility](https://ziglang.org/documentation/master/#Lifetime-and-Ownership) · [Odin allocators](https://odin-lang.org/docs/overview/#allocators) · [C3 memory](https://c3-lang.org/language-common/memory/)

Blood has no verified public memory specification or runnable implementation in this review. DIL's available material describes a UI DSL and does not establish an independent native memory model. Neither supports a conclusion about this three-part goal. [Blood note](../languages/blood.md) · [DIL note](../languages/dil.md)

## What would establish a stronger breakthrough

The most persuasive result would combine a clear safe subset, minimal source-level bookkeeping, a specified reclamation policy, and reproducible allocation/liveness measurements across unique and shared trees, cyclic graphs, variable-size records, long-lived deletion workloads, and cross-thread transfers. The comparison must include well-designed arenas and pooling in C/Rust, as well as idiomatic per-object allocation.

The existing evidence favors **Goose for region-shaped data and compact representation**, and **Koka/Lean-style automatic counting and reuse for functional programs**. Both remove substantial manual work. A requirement for unrestricted graphs and prompt automatic reclamation introduces further costs or restrictions that must be evaluated explicitly; it is not evidence that the original three goals are logically incompatible.
