# Goose-style data stacks with a GC fallback

English | [简体中文](goose-hybrid-gc.zh-CN.md)

Research date: 2026-11-14. This is an architectural assessment, not an implemented Goose extension or a new benchmark. Goose-specific baseline claims refer to the previously inspected `32a4f445d8a94b22874a28469f95f69ba3ac31dd`; the [stack-assignment experiments](../experiments/goose-stacks-2026-11-11/README.md) used `f4637bf` on November 11. This note does not claim to audit every subsequent upstream change.

**This is a promising direction when automatic memory safety and low source-level bookkeeping matter more than an absolute prohibition on GC.** Statically justified data-stack placement can keep inexpensive allocation, compact data, and bulk release for suitable values. A tracing collector can handle objects whose dynamic sharing and independent lifetimes would otherwise require explicit ownership relationships or deletion protocols. Better overall performance is a hypothesis to measure, not a consequence of adding both mechanisms.

## The principle already has substantial precedent

MLKit combines region inference with garbage collection. Elsman and Hallenberg's 2021 work integrates generational collection with typed regions and compact representations. Its strategy avoids generational write barriers by scanning designated mutable regions; this trades update bookkeeping for collection-time work and should not be read as universally free mutation. The MLKit representation and type system are different from Goose's. [2021 paper](https://elsman.com/mlkit/pdf/jfp2021.pdf)

The later PLDI 2023 paper identifies and repairs a soundness problem in earlier region/GC typing results involving higher-order polymorphic programs. A region pointer that program code will never dereference may still be visited by the collector through a live closure or object. Collector safety therefore needs stronger conditions than just proving application accesses safe. The new design should use the repaired reasoning rather than treating all earlier proofs as sufficient. [2023 safety paper](https://elsman.com/mlkit/pdf/gcsafe-pldi23.pdf)

Go's standard implementation is a familiar example of automatic stack placement with GC-managed heap allocation when a local's lifetime cannot be proven confined to the stack. Goose's potential contribution would be the richer multi-data-stack placement, destination construction, and compact variable-size layout that could keep more dynamic data off a traced heap. How much more, and at what compilation cost, remains unmeasured. [Go allocation FAQ](https://go.dev/doc/faq#stack_or_heap) · [Goose storage model](https://github.com/aardappel/goose/blob/32a4f445d8a94b22874a28469f95f69ba3ac31dd/docs/reference.md#4-where-values-live)

## Who selects a data stack?

Goose determines stack requirements and safe placement rules at compile time, but its current C backend passes stack identities at runtime. It does not permanently bind every local in a shared function body to an absolute global stack number. The inspected `f4637bf` implementation uses a hidden `gs_sp` base index and constant per-function offsets: a local addresses `gs_stks[gs_sp + k]`, and a callee receives a base above the caller's occupied indices. The compiler computes the required stack count. [Code generation model](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/src/codegen.h#L20) · [Live specification, §10.3](https://aardappel.github.io/goose/docs/goose_spec.html#103-stack-assignment-deterministic-recipe)

Conceptually, omitting other temporaries and result destinations:

```text
work(base):
    a uses S[base + 0]
    {
        b uses S[base + 1]
        child receives base + 2 for its local stacks
    }
    c can reuse S[base + 1]
```

The offsets and reuse points are determined during compilation; the passed base identifies the concrete stacks for this call. Scope exit restores byte tops and releases the corresponding index range for subsequent scopes. Last use alone need not end the owner's scope. [Scope and index management](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/src/codegen_frames.h#L1077)

Stack assignment follows storage owners, nesting, and independent growth, rather than object type or size buckets. Many inline elements can occupy one container's stack. A reference used to grow an existing value carries that value's stack identity; a nonfixed result receives a caller-selected destination stack separately from the callee's local-stack base. Neither operation searches for an unused stack or reruns lifetime inference. At runtime, byte counts, top pointers, physical addresses, and committed pages vary. Each worker instance has its own stack storage, with requirements computed for its thread program. [Implementation notes](https://aardappel.github.io/goose/docs/goose_spec.html#appendix-e-implementation-notes-informative)

The recursion restrictions keep the stack count statically bounded. Runtime-created stacks for independently growable nested elements remain a future feature in §11.3. A proposed hybrid could instead create a region instance when a task starts and pass an implicit region handle through its calls, while proving reference validity statically. That extension would change runtime storage instantiation without requiring a runtime heuristic to guess each object's lifetime. It is a design option, not current Goose behavior.

## Which workloads each storage path can cover

The following is a design assessment of the proposed hybrid, not a claim that Goose already implements all these paths. Escape analysis is only part of the implementation: choosing a data stack also requires region/lifetime inference, compatible growth and aliasing rules, and often caller-provided destinations.

- **Native call stack:** small fixed-size locals, temporary records, bounded scratch arrays, and referenced values whose uses remain within a valid activation. Taking an address does not itself force GC. Large or runtime-sized buffers may be better placed on data stacks even when they do not escape. Some values are held in registers, scalar-replaced, or eliminated altogether; those are separate outcomes, not additional stack allocations. [Go's placement explanation](https://go.dev/doc/faq#stack_or_heap)
- **Multiple data stacks:** independently growing strings and arrays; large temporary buffers; request parsing, serialization, query batches, frame scratch, and compiler-pass data that can be released together. A fresh result can be built in a caller's destination and outlive the constructing function. Multiple stacks let a growing result coexist with shorter-lived scratch or another independently growing result. A tree or even a cyclic graph can use scoped storage if its references and representation permit collective release; cycles alone do not require tracing.
- **GC-managed objects:** callbacks or closures retained by unrelated clients; cross-request caches with independently expiring entries; incremental dependency graphs; long-lived mutable graphs in which arbitrary subsets survive. GC is also the conservative fallback when the compiler cannot prove a valid cheaper placement. A permanently live lookup table does not need GC simply because it lives a long time; the difficult case is changing reachability combined with independent reclamation needs.

These paths can coexist inside one subsystem. A request handler could keep counters and small records on the call stack, parsing and formatting payloads on several data stacks, and a retained cache entry in GC storage. A slice descriptor on the call stack does not put its backing buffer there. Retaining a view into a temporary buffer requires a safe storage decision for that buffer and its dependencies, or an explicit copy when semantics allow it.

Structured child tasks could share a task-scoped region if all users finish before release and the runtime preserves that storage across suspension. Arbitrarily interleaved suspended tasks cannot simply share one rewound stack. Task-specific stacks, detachable regions, and transfer protocols are additional design work, not features established by the existing Goose probes. Likewise, a fixed number of data stacks does not provide arbitrarily many independently reclaimable runtime objects.

The strongest candidates for a high non-GC share are bounded batch pipelines and frame/request scratch. Persistent UI state, shared caches, and incremental analysis usually provide more work for GC, while their temporary computations may still use data stacks. These are workload hypotheses, not measured industry-wide percentages. A compiler that keeps one AST per compilation and an IDE that retains revisions have substantially different lifetimes despite both processing syntax trees.

## What a coverage percentage needs to measure

There is no justified universal split such as 20% native stack, 70% data stacks, and 10% GC. Measure at least these separately:

- **Dynamic allocation events and payload bytes by destination.** State whether the denominator is actual storage after optimization or a common baseline of logical allocations. Record eliminated allocations separately. Count a bump allocation as an event even though it makes no allocator-library call; distinguish payload from capacity, metadata, and collector copies. Static data and foreign allocations need a declared separate scope.
- **Live and retained memory over time.** Dead values below a live data-stack top can remain retained until the scope ends. Report peak residency and retained dead bytes, not merely the proportion diverted from GC; virtual address reservations are not RSS.
- **Collector and total cost.** Roots, pointer density, long-lived graphs, barriers, and collection policy can outweigh a low rate of new GC allocation. Track GC CPU and pauses, total throughput/tail latency, and analysis/compilation time.

A conditional example makes the distinction concrete: if one request creates 100 MiB of eligible temporary payload and 1 MiB of independently retained payload, placing the former on data stacks and the latter in GC gives about **99% versus 1% of those payload bytes**. This is arithmetic under stated assumptions, not a benchmark or a three-way split including native locals. If results accumulate across requests while scratch is reused, GC can nevertheless account for most of the long-term resident memory. If retained results point back into scratch, the assumed placement may not be legal at all.

## Published measurements show the range, not a prediction

Choi et al.'s 2003 Java prototype reported a median **19%** stack-allocatable share of dynamically created user-code objects across ten benchmarks; three exceeded **70%**. This is historical object-count evidence, not byte coverage or a forecast for Go or Goose. [Paper, abstract](https://www4.cs.fau.de/~isa/choi_stack_allocation.pdf)

MLKit's 2021 Figure 16 reports **bytes reclaimed by GC**, versus region inference. With regions plus generational GC (`rG`), the reported GC shares are **3% for `ray`, 53% for `msort`, and 94% for `nucleic`**. Region-friendly `msort-rf` reports **7%**; it copies list tails to avoid sharing between inputs and output. These are rounded reclamation shares, not allocation destinations. MLKit collects within regions and the figure does not separate native-stack allocation. The values therefore cannot be combined with the Java percentages into a three-way estimate. [Paper, §5 and Figure 16](https://elsman.com/mlkit/pdf/jfp2021.pdf#page=24)

For this project, no representative three-way coverage measurement exists yet. The [eight Goose probes](../experiments/goose-stacks-2026-11-11/README.md) test placement and rejection rules, without sampling representative application allocations. A useful next experiment would attribute allocations in a parser/request pipeline, an incremental graph, and a mixed retained-result workload, keeping automatically inferred placement separate from source rewrites introduced to improve it.

## Additional evidence: inferred regions and transaction scopes

Cherem and Rugina's ISMM 2004 Table 3 reports stack/region allocation shares of **97%/1% for `power`, 22%/66% for `bh`, 22%/78% for `health`, 0%/99% for `perimeter`, and 0%/0% for `em3d`**. The remainder is immortal storage, not a measured GC share. Size-weighted average lifetimes cover regions and stack data together: `bh` reports 1%, `perimeter` 100%. Table 2 also shows essentially unchanged peak application memory for `perimeter` with GC, regions, or no reclamation. Long region lifetimes do not by themselves demonstrate avoidable retention. The system uses nonlexical regions and permits dangling references proven unused by the program, so its results do not directly establish Goose-stack coverage or collector safety. [Paper, §§1 and 7, Tables 2–3](https://citeseerx.ist.psu.edu/document?doi=efc67b4a7f6dbb20370afd4234d62ead890f821c&repid=rep1&type=pdf)

Stancu et al.'s ISMM 2015 SPECjbb2005 study uses seven phase annotations. Figure 9 reports **77.30%–77.62% “Region freed memory”**. Retain that label: dividing its displayed region-freed bytes by allocated bytes gives approximately **76.52%–76.84%**, and the percentage denominator is not reconciled here. Regions participate in GC; surviving objects move to global storage and active regions become inactive until reentered. At a 128 MB young generation, both hybrid variants report 77.62%, yet execution times are **120.75 s for normal GC, 133.38 s for allocation-table mapping, and 119.12 s for normalized offsets**. Coverage does not determine performance. [Paper, §4.2 and Figure 9](https://www.unibw.de/ucsrl/pubs/ismm15.pdf)

These studies strengthen the case for a prototype with phase-local allocation. They do not establish universal percentages, annotation-free inference at the same precision, or modern C/Rust execution and Go/Zig compilation performance. The GC within active regions in the second study is also a different architectural option from keeping data stacks wholly outside collection.

For an experiment, hold representation, inlining, scalar replacement, workload, and input constant between **escape analysis + call stack + GC** and the version adding region inference. Attribute the baseline GC allocation bytes diverted into data stacks, while recording changes in copies, retained memory, root scanning, total runtime, and compile time. If layout optimization is added too, measure it as a separate factor. Partial escape analysis can already eliminate allocations on nonescaping paths; do not credit that reduction to regions. [Stadler et al., CGO 2014](https://www.ssw.uni-linz.ac.at/Research/Papers/Stadler14/Stadler2014-CGO-PEA.pdf)

When citing Goose's present restrictions, distinguish growable storage from all nonfixed locals: the live specification's §7.8 prohibits both variable- and resizable-class local owners from remaining in scope across a recursive-cycle call. A variable-size value whose length is fixed after construction still falls under this rule. Root structs, static function values, and worker isolation also have separate representation and compilation restrictions that adding a collector would not automatically remove. [Goose specification, §7.8](https://aardappel.github.io/goose/docs/goose_spec.html#78-recursion)

## Automatic placement should be a compiler decision first

The proposed rule is to place a value or allocation family on a data stack when its lifetime, growth, reference relationships, and representation satisfy the stack invariants. Otherwise allocate it in GC-managed storage from construction, with conservative inference accepted as a performance cost. An escaping value is not automatically a GC allocation: returning a fresh value into the caller's destination may already solve its lifetime. Conversely, a proven scope lifetime does not by itself establish that a useful data-stack representation exists.

Do not implement the fallback as an unconditional runtime move after a reference has escaped. Moving an already-aliased mutable object requires preserving identity, updating aliases, and handling interior and relative pointers. Moving an object together with its dependency graph may be necessary. Explicit copies are appropriate only where independent-value semantics permit them. A first implementation should classify potentially escaping allocation sites before execution; runtime promotion can be a later, separately specified optimization.

Source semantics should remain stable across placement choices: observable identity, aliasing, mutation, and resource cleanup cannot depend on whether an optimization succeeded. Storage-sensitive APIs, raw addresses, FFI, and persistent layouts need explicit contracts. Functions may need storage-polymorphic implementations or a common representation at their boundaries; introducing a GC branch does not automatically make all existing Goose representations interchangeable.

## The cross-memory reference rules are the critical part

- **Data stack to GC object:** the reference must be represented in the collector's live roots, through generated root maps, registered slots, or precisely traced region descriptors. Raw byte buffers with no GC references can remain unscanned. A stack-allocated container holding GC references is not automatically outside collection work.
- **Long-lived GC object to short-lived data stack:** disallow this edge unless the target's lifetime is proven sufficient, or arrange compatible storage for the complete escaping dependency. A collector cannot keep an independently rewound data stack alive merely by observing its address. Whole-region lifetime extension is possible but may retain much more than the referenced value.
- **GC object to GC object:** normal tracing rules apply. Generational or concurrent collection may require write barriers or another sound edge-tracking strategy. Cycles can be collected when unreachable from all roots.
- **Data stack to data stack:** retain Goose-style root and scope checking. Adding GC must not weaken the existing rules for shrinking, retyping, or preserving interior references.

Collectors also need valid descriptions of partial construction, temporary values, and abandoned slots at each collection point. Application liveness and collector-visible reachability must agree about which pointer fields are valid. Exact handling of Goose's packed variable-size values, relative links, and interior pointers requires compiler support; scanning arbitrary words as if all references were ordinary aligned addresses is insufficient.

## Choose the collection unit deliberately

GC can own an entire compact document or region as one unit, allowing its lifetime to escape a lexical scope while retaining inline layout. That is useful, but it does not reclaim dead nodes individually while any live view retains the unit. This would leave the long-lived-container problem only partly addressed.

For independently dying entities, use independently traceable objects or chunks with suitable subobject metadata. Their payloads can still inline strings and small arrays. The collector needs a defined mapping from any valid interior reference to the object that owns it. Reclaiming arbitrary interior holes requires additional layout machinery; putting one GC header on a giant arena does not provide it.

Moving collection complicates stable references, FFI, and relative offsets across collection units. A precise nonmoving mark-and-sweep collector is a reasonable first prototype choice because it reduces relocation work, but it adds metadata, sweep cost, and fragmentation. It also does not solve growth of an existing contiguous object: stable growable arrays still need an appropriate reservation, chunking, indirection, or update protocol. Nonmoving collection means the collector does not move an object; it does not make every container resize nonmoving.

## Keep the cost boundary visible

Reducing traced-heap allocation can reduce collection frequency and work, but the result depends on allocation rate, live objects, roots, pointer density, retention, and the chosen collection policy. A small proportion of GC allocations can still produce a large persistent object graph or expensive root scans. A numerical rule such as “10% of allocations use GC, therefore 10% of the GC cost remains” is not justified. [Go GC cost guide](https://go.dev/doc/gc-guide)

Pure data-stack paths with no GC references can avoid much collector bookkeeping. Mixed paths can still require roots, safe points, and collector-specific barriers. Concurrent and generational collectors trade pause time, synchronization, memory headroom, and implementation complexity. Existing Goose integer-loop timings cannot predict these costs.

Use automatic placement by default, accompanied by an allocation report explaining which values went to the GC heap and why. Offer a transitive **no-GC-allocation contract** for selected functions or modules; violations should be errors rather than silently changing storage policy. This contract does not promise no GC pause, because a function may hold roots or run in a process whose other tasks trigger collection. Stronger isolation or latency guarantees require a separate runtime design.

Also keep deterministic file, lock, device, and cancellation cleanup distinct from memory collection. GC prevents reclamation of reachable storage; it does not automatically bound tail latency, close resources at the required moment, or make shared mutation race-free. It cannot collect data still reachable from a cache merely because the application no longer considers it useful.

## A practical implementation sequence

Start with a single-worker collector and keep existing worker isolation. Add precise root registration and tracing metadata, a conservative compile-time allocation classification, and a nonmoving collector for a restricted set of object layouts. Forbid unsafe cross-memory edges instead of attempting arbitrary runtime promotion. Test mixed-reference chains and cycles, live closures containing dead source-level references, interior pointers, shrinking, partial initialization, and FFI-held references.

Then support additional layouts and storage-polymorphic APIs, and optimize classification using cached interprocedural summaries. GC fallback can let a bounded analysis accept a program safely without solving every lifetime relationship statically, but it does not remove representation and interface constraints. Inspect compilation times and diagnostics before claiming Go/Zig-like development speed.

Worker-local heaps are a promising way to localize collection while preserving isolation. Cross-worker graph transfer or immutable sharing still needs an explicit ownership/root protocol; a local collector does not make unrestricted cross-worker references safe. Verona's isolated-region research provides related ideas about localizing memory-management policies, with its own capability restrictions. [Verona research](https://arxiv.org/abs/2309.02983)

Evaluate a mostly scoped parser pipeline, a cyclic long-lived graph with churn, and a mixed workload that retains views or closures from temporary computations. Compare pure Goose where the task is expressible, the hybrid with placement optimization on and off, Go, and well-designed C/Rust storage. Measure allocations by domain, roots scanned, live and retained bytes, RSS, throughput, collection and tail latency, barriers, clean/incremental builds, and required source-level management. A hybrid wins only if its extra machinery is outweighed by measurable gains in usable workloads.

For the user's goals, this is worth prioritizing as an alternative to making all long-lived graphs obey manual region/deletion protocols. The intended outcome is ordinary code with automatic lifetime management, an inexpensive data-stack path where justified, and explicit performance contracts for critical code. It is not a promise that arbitrary code receives Goose's present data-stack costs.
