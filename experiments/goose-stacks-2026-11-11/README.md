# Goose data-stack assignment and lifetime checks

Measured on 2026-11-11 with Goose `f4637bfb342fb70d42bea0474eab9e62a3c99d68`, on macOS/arm64. [Raw results](results.json) include compiler versions, all probe sources, static stack reports, native exit statuses, and negative diagnostics.

Run with Python 3, Clang, and the specified Goose compiler:

```sh
python3 experiments/goose-stacks-2026-11-11/run.py --goose-bin /path/to/goose
```

The runner uses a temporary directory and an isolated Goose runtime cache. Six positive programs are compiled with `build -O2 --offline --stacks`, then executed with assertions. Two negative programs are checked and must produce the expected lifetime diagnostics. The runner verifies the compiler revision.

## Observations

- Three simultaneously live growable arrays: **3 data stacks**.
- Three growable arrays in successive independent blocks: **1 data stack**, reused across blocks.
- Three arrays declared and last-used sequentially in the same block: **3 data stacks**. The reported allocation follows owning scopes rather than automatically shortening them to last use in this example.
- One result array outside a loop plus scratch inside 100 iterations: **2 data stacks**. The result has 100 values with checksum 4950; scratch is scoped to an iteration.
- A function constructing a returned array while holding local scratch: **2 data stacks**, covering the result destination and callee scratch; the returned element is 10.
- Clearing an array after the last use of an interior reference: **1 data stack**, accepted; the asserted length after clearing is zero.
- Clearing before the reference's last use: **rejected**.
- Assigning an inner array's view to an outer binding: **rejected**, rather than implicitly copying or extending the inner owner's lifetime.

Assertions replace formatted printing in positive probes because printing itself needs temporary storage and changes the stack report. An exploratory version with three containers and `print` reported four stacks; this was measurement overhead, not an extra owner for the data under study.

## Interpretation and limits

These checks support a concrete distinction between automatic physical stack assignment, reference-validity analysis, and the owning scopes expressed by a program. Multiple stacks isolate independently growing containers, and disjoint scopes reuse storage. They do not establish automatic per-element reclamation, optimal lifetime partitioning, or independent regions for arbitrary runtime-created graph nodes.

The counts are the compiler's pre-native-optimization report, not a measurement of touched pages, allocator calls, RSS, or execution speed. Native assertions verify the expected small examples; they are not a full compiler or runtime safety proof. No new performance benchmark or page-trimming measurement is included.

The separately inspected newer source `32a4f445d8a94b22874a28469f95f69ba3ac31dd` describes the same relevant rules in [stack assignment](https://github.com/aardappel/goose/blob/32a4f445d8a94b22874a28469f95f69ba3ac31dd/docs/goose_spec.md#103-stack-assignment-deterministic-recipe). It also documents that rewinding normally retains committed pages and that `os.trim_memory()` can discard unused complete pages. This is different from reclaiming holes below live data. [Memory model](https://github.com/aardappel/goose/blob/32a4f445d8a94b22874a28469f95f69ba3ac31dd/docs/goose_spec.md#12-memory-model)
