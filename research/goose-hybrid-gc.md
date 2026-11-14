# Goose-style data stacks with a GC fallback

English | [简体中文](goose-hybrid-gc.zh-CN.md)

Research date: 2026-11-14. This is an architectural assessment, not an implemented Goose extension or a new benchmark. Goose-specific baseline claims refer to the previously inspected `32a4f445d8a94b22874a28469f95f69ba3ac31dd`; the [stack-assignment experiments](../experiments/goose-stacks-2026-11-11/README.md) used `f4637bf` on November 11. This note does not claim to audit every subsequent upstream change.

**This is a promising direction when automatic memory safety and low source-level bookkeeping matter more than an absolute prohibition on GC.** Statically justified data-stack placement can keep inexpensive allocation, compact data, and bulk release for suitable values. A tracing collector can handle objects whose dynamic sharing and independent lifetimes would otherwise require explicit ownership relationships or deletion protocols. Better overall performance is a hypothesis to measure, not a consequence of adding both mechanisms.

## The principle already has substantial precedent

MLKit combines region inference with garbage collection. Elsman and Hallenberg's 2021 work integrates generational collection with typed regions and compact representations. Its strategy avoids generational write barriers by scanning designated mutable regions; this trades update bookkeeping for collection-time work and should not be read as universally free mutation. The MLKit representation and type system are different from Goose's. [2021 paper](https://elsman.com/mlkit/pdf/jfp2021.pdf)

The later PLDI 2023 paper identifies and repairs a soundness problem in earlier region/GC typing results involving higher-order polymorphic programs. A region pointer that program code will never dereference may still be visited by the collector through a live closure or object. Collector safety therefore needs stronger conditions than just proving application accesses safe. The new design should use the repaired reasoning rather than treating all earlier proofs as sufficient. [2023 safety paper](https://elsman.com/mlkit/pdf/gcsafe-pldi23.pdf)

Go's standard implementation is a familiar example of automatic stack placement with GC-managed heap allocation when a local's lifetime cannot be proven confined to the stack. Goose's potential contribution would be the richer multi-data-stack placement, destination construction, and compact variable-size layout that could keep more dynamic data off a traced heap. How much more, and at what compilation cost, remains unmeasured. [Go allocation FAQ](https://go.dev/doc/faq#stack_or_heap) · [Goose storage model](https://github.com/aardappel/goose/blob/32a4f445d8a94b22874a28469f95f69ba3ac31dd/docs/reference.md#4-where-values-live)

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
