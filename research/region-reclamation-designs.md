# Designs for independent lifetimes inside regions

English | [简体中文](region-reclamation-designs.zh-CN.md)

Research date: 2026-11-11. This is a design exploration following [the Goose study](beyond-goose.md), supported by primary descriptions of existing mechanisms. The proposed combination is not implemented or proven, and no new performance experiment was run.

## Separate three questions

An extension to Goose must distinguish **when an object should cease to exist**, **when its storage is no longer being accessed**, and **how that storage is reused or returned**. A pool or allocator answers the third question. A generation check verifies identity at lookup. A safe access interval answers part of the second question. None of these alone discovers that an arbitrary graph node is unreachable.

The most promising strict no-tracing/no-per-object-RC design combines Goose's scoped data stacks with **reclaimable long-lived stores, lifetime relationships, and short access phases**. The intent is to automate storage and access safety while concentrating lifetime decisions in data-model declarations and a few domain operations. It does not eliminate those decisions.

## Reclaimable stores: regions with individual deletion

Keep ordinary scoped values on Goose-style data stacks. Place independently deletable entities in a separate store backed by reusable chunks, slots, and size classes or span allocation for variable-size payloads. Reuse slots on deletion; release empty chunks when their metadata and outstanding accesses allow it. An allocation may need to acquire a new chunk, and fragmentation remains possible. This adds an allocator to the language's storage options, although it need not call a general-purpose allocator once per object.

Reaps provide established allocator-level precedent: they combine region-wide reclamation with individual object deletion. They do not by themselves supply a memory-safe language, infer deletion, or guarantee compact storage. The 2002 paper's performance findings are not a modern Goose comparison. [Reaps paper](https://people.cs.umass.edu/~emery/pubs/berger-oopsla2002.pdf)

External links into a deletable store should be checked handles. Physical views are temporary. Moving payloads behind a stable slot table is possible only when no views or retained foreign pointers prevent it; it costs indirection and relocation. Identity metadata must remain valid for lookup, including after store destruction and address reuse. Retire exhausted generation identities instead of assuming wraparound cannot happen.

## Lifetime relationships: make the deletion decision coarse and declarative

Use two distinct kinds of relationship. An owning relation controls a child's lifetime; an observing relation identifies an object without keeping it alive. For example, a document owns its syntax nodes, while navigation links and an editor selection observe nodes through handles. Deleting a subtree schedules deletion of its owned descendants, and observers subsequently see absence.

A simple core can require owning relations to form a forest, with one parent per mutable entity and no ownership cycles. Observing links may form arbitrary cycles. Containment can supply common ownership defaults, but reparenting and genuinely shared lifetime requirements need explicit policies. The language must check or maintain the ownership invariant during updates. This replaces pointer bookkeeping with data-model choices; it cannot infer what the application considers obsolete.

Flecs has concrete relationship cleanup policies, including deleting children when a parent is deleted. These are precedent for declarative cleanup, not a claim that Flecs is a memory-safe language. Vale separately illustrates that non-owning references can coexist with single ownership; its guide still requires one owning reference for each mutable struct. Neither example removes ownership semantics. [Flecs cleanup policies](https://www.flecs.dev/flecs/ComponentTraits.html) · [Vale reference model](https://vale.dev/guide/references)

Cascade cleanup is proportional to the work required: children, indexes, relationships, and resources may all need processing. Region storage reset does not make that semantic cleanup constant-time.

## Access phases: keep views valid and commit structural changes later

The proposed first implementation would give each store one controlling task. Entering a short access phase permits checked handles to produce physical views. The compiler binds those views to the phase, rejects escapes and suspension with live views, and prevents callbacks from bypassing the phase's structural-change restrictions. Multiple aliases to unchanged-layout data can remain usable within the phase. Writes still need separate rules if tasks execute concurrently.

Insertion operations that would relocate existing data, deletion, retyping, and compaction are either prohibited during access or queued. The simplest deletion contract is **deletion takes effect at the outermost phase's commit**, not immediately when requested. Existing views stay valid until the phase ends; new lookups during that phase follow the same pre-commit structural state. At commit, after all views have ended, apply deletions, invalidate handles, run defined cleanup, and make storage reusable. Define duplicate commands, callback reentrancy, errors, and cancellation rather than leaving them implicit.

Illustrative syntax only; this is not Goose code:

```text
phase(store) {
    if let node = store.get(id) {
        update_fields(node)
        store.defer_delete(id)
        inspect(node)              // valid until this phase ends
    }
}                                  // commit deletion; old id now fails lookup
```

Flecs staging already queues structural operations to keep iteration valid, and explicitly documents that deferred operations can change when updates become observable. A language could check the corresponding access restrictions across functions instead of relying solely on library usage discipline. This is a proposal for a small language-level protocol, not a proof of the full design. [Flecs staging](https://www.flecs.dev/flecs/Systems.html#staging)

This can avoid reference counting on every handle copy and permits physical-reference loops within a phase after validation. It adds phase boundaries, a command buffer, deferred visibility, and cleanup latency. Long or stalled phases delay reclamation. Bounds on pending commands need backpressure or failure; automatically committing while views remain live would violate the contract. If immediate deletion visibility is essential, a different API can invalidate future lookups immediately while retaining old payloads until readers finish, but its snapshot and mutation semantics must be specified separately.

## Concurrent readers: reclamation protocols do not supply a complete concurrency model

For a later extension, RCU or epoch-based reclamation can separate removal from physical destruction. They wait until relevant readers have finished before freeing retired storage. They do not find arbitrary unreachable objects, and they do not by themselves make conflicting reads and writes safe. Published versions must use an appropriate immutable-update, atomic, lock, or other synchronization discipline. [Linux RCU concepts](https://www.kernel.org/doc/html/latest/RCU/rcu.html) · [RCU non-guarantees](https://www.kernel.org/doc/html/latest/RCU/Design/Requirements/Requirements.html)

Crossbeam documents that a pinned participant delays reclamation of newly removed objects. Therefore, an access phase cannot simply become an indefinitely suspended async task without consequences. Use bounded access intervals, or transfer buffers to an operation owner whose storage survives until actual completion. Cancellation requests alone are not completion. RCU/epochs are not tracing collectors, but they are runtime reclamation machinery and some libraries call them GC. [Crossbeam epoch management](https://docs.rs/crossbeam/latest/crossbeam/epoch/index.html)

The no-RC core should initially use one owner per mutable store plus structured immutable sharing or whole-store transfer. A handle's identity does not grant access after transfer: lookup also needs the current authority. Shared mutable stores are a separate extension, with their own synchronization and reclamation proof obligations.

## Improvements for scoped data and small retained views

Liveness-based owner shortening could improve Goose's same-block stack reuse when the compiler proves the owner and every alias are dead. Keep this optimization limited to values whose earlier storage release cannot observably change resource cleanup or foreign access. Inference can also suggest a smaller scope where automatic shortening is not justified. This does not reclaim independently dead elements of a still-live container.

For a small retained slice, offer a distinct owned-value operation that copies the selected data into an appropriate destination. Immutable value APIs may support an explicit policy for detaching small slices from large backing buffers. Preserve view identity, mutability, and aliasing semantics; a mutable view must not silently become a detached copy. Chunked input can reduce retained backing storage, at the cost of boundary handling and loss of a universally contiguous representation.

## Fully automatic arbitrary graphs require another policy

If users require arbitrary strong cycles and automatic reclamation after the last external path disappears, without declaring a lifetime owner or issuing domain deletion, the above core is insufficient. A region-local tracing collector is a direct optional solution: trace from registered roots and reclaim unreachable nodes within a selected store. Cross-region incoming strong references must be represented as roots or otherwise participate in the lifetime protocol. Isolation can localize pauses; it does not make scanning, barriers, metadata, or resource cleanup free.

That option is GC and fails a strict no-GC requirement. Reference counting with a cycle strategy is another option, with its own costs. Neither should be inserted invisibly under an API advertised as having the core's reclamation guarantees. A hybrid design can make these distinct store policies explicit and keep scoped data on the inexpensive path.

## Recommended prototype boundary

Start with Goose-style scoped stacks plus a single-owner deletable store. Add checked identity, a small ownership/observation schema, and synchronous access phases with deferred structural edits. Keep compiler inference focused on reference validity, phase escape, and safe storage reuse. Handle recursive payloads and variable-size data through the store allocator instead of requiring every entity to own a statically numbered data stack.

Then test the difficult cases: delete through a callback while a view is live, reparent into a descendant, commit failure, deletion with external observing handles, store transfer with copied handles, freeing a store while handles survive, generation exhaustion, and cancellation with in-flight I/O. Measure retention and tail latency during long phases, metadata and indirection, fragmentation, and the source annotations or restructuring needed. Prove the small protocol before extending it to concurrent mutation or arbitrary automatic graph collection.

This combination can address independent deletion and safe reuse while reducing manual bookkeeping. Its principal boundary is explicit: application relationships or domain operations decide lifetime; the compiler and runtime arrange safe access and reclamation.
