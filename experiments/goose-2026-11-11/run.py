#!/usr/bin/env python3
"""Probe Goose lifetimes, reflection and threads; compare a native integer loop."""

import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile

REFERENCE = Path(__file__).resolve().parents[1] / "bend-2026-11-11/run.py"
SPEC = importlib.util.spec_from_file_location("integer_loop_reference", REFERENCE)
reference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reference)
SOURCE_COMMIT = "f4637bfb342fb70d42bea0474eab9e62a3c99d68"
GOOSE_SOURCE = """fn main() {
    var x: u32 = 1;
    for i in 50000000 {
        x = x ^ (x << 13);
        x = x ^ (x >> 17);
        x = x ^ (x << 5);
    }
    print(x);
}
"""
NEGATIVE = {
    "type_mismatch": ('fn main() { let x: i64 = "wrong"; print(x); }', "expected a value of type i64"),
    "escape": ('fn main() { var outer: u8[>..] = []; var w = outer[..]; { var inner: u8[>..] = [1]; w = inner[..]; } print(w.len); }', "does not outlive the destination"),
    "shrink_with_reference": ('fn main() { var xs: i64[>..] = [1]; let first .= xs[0]; xs.clear(); print(first); }', "cannot clear xs while first is still used"),
    "const_write": ('fn main() { const xs = [1,2]; xs[0] = 3; print(xs); }', "cannot assign through this path"),
}
POSITIVE = {
    "stable_growth": ('fn main() { var xs: i64[>..] = []; let first .= xs.push(1); for i in 10000 { xs.push(i); } first = 7; print(first, " ", xs[0]); }', "7 7"),
    "field_reflection": ('struct Pair { a: i64, b: i64 } fn count_fields<T>() -> i64 { var n = 0; const for <N,A> in fields<T> { n += 1; } return n; } fn main() { print(count_fields<Pair>()); }', "2"),
    "thread_isolation": ('var counter: i64 = 1; thread_fn worker() { counter = 7; qput(counter); } fn main() { let id = thread_spawn(worker); let value = qget<i64>(); thread_wait(id); print(counter, " ", value); }', "1 7"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goose-bin", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results.json"))
    args = parser.parse_args()
    goose = args.goose_bin.absolute()
    tools = {name: shutil.which(name) for name in ("clang", "rustc", "go", "zig")}
    if not all(tools.values()):
        raise RuntimeError(f"Missing toolchains: {tools}")
    env = dict(os.environ)
    data = {"measured_at": datetime.datetime.now().astimezone().isoformat(), "source_commit": SOURCE_COMMIT,
            "tools": {}, "probes": {}, "benchmark": {}, "method": {
                "build_runs": 5, "execution_runs": 7, "warmups": 1, "iterations": reference.ITERATIONS,
                "expected_output": reference.EXPECTED,
                "builds": "Serial round-robin, fresh source name/comment each time; warm toolchains, filesystem, and Goose runtime cache; fresh Zig local cache, incremental off",
                "optimization": "Goose -O2 to C then Clang -O2 via goose build; C -O3; Rust opt-level=3; Go defaults; Zig ReleaseFast",
                "scope": "Native CPU scalar loop; process startup and output included; no large-project, allocation, or multicore benchmark",
            }}
    with tempfile.TemporaryDirectory(prefix="goose-research-") as directory:
        work = Path(directory)
        env["GOOSE_HOME"] = str(work / "goose-home")

        def run(command):
            return reference.execute([str(v) for v in command], work, env)

        def checked(command):
            result = run(command)
            reference.require_success(result, str(command))
            return result

        def norm(text):
            return text.replace(str(goose), "{goose}").replace(str(work), "{work}")

        def build(source, binary):
            return [goose, "build", source, "-O2", "--offline", "--cc", tools["clang"], "-o", binary]

        data["tools"]["goose"] = checked([goose, "version"])["stdout"]
        if SOURCE_COMMIT[:7] not in data["tools"]["goose"]:
            raise RuntimeError("Compiler does not report the expected source revision")
        for name in tools:
            flag = "version" if name in ("go", "zig") else "--version"
            data["tools"][name] = checked([tools[name], flag])["stdout"].splitlines()[0]
        for name in ("machdep.cpu.brand_string", "hw.memsize", "hw.ncpu"):
            data[name] = checked(["sysctl", "-n", name])["stdout"]
        cold = work / "cold.goose"
        cold.write_text(GOOSE_SOURCE)
        data["first_build_empty_runtime_cache"] = checked(build(cold, work / "cold"))["seconds"]
        for name, (body, marker) in NEGATIVE.items():
            source = work / f"{name}.goose"
            source.write_text(body + "\n")
            result = run([goose, "check", source, "--offline"])
            result["matches_expectation"] = result["exit_code"] == 1 and marker in result["stderr"]
            result["stderr"] = norm(result["stderr"])
            data["probes"][name] = result
        for name, (body, expected) in POSITIVE.items():
            source = work / f"{name}.goose"
            source.write_text(body + "\n")
            compiled = checked(build(source, work / name))
            result = checked([work / name])
            result["matches_expectation"] = result["stdout"] == expected
            result["build_stderr"] = norm(compiled["stderr"])
            data["probes"][name] = result
        source = work / "bounds.goose"
        source.write_text("fn main() { let xs: i64[2] = [1,2]; print(xs[3]); }\n")
        checked(build(source, work / "bounds"))
        result = run([work / "bounds"])
        result["stderr"] = norm(result["stderr"])
        result["matches_expectation"] = result["exit_code"] == 1 and "bound" in result["stderr"]
        data["probes"]["bounds"] = result
        if not all(v["matches_expectation"] for v in data["probes"].values()):
            raise RuntimeError(f"Unexpected probe results: {data['probes']}")
        print("all eight probes passed", flush=True)
        sources = {"goose": GOOSE_SOURCE, **{k: reference.SOURCES[k] for k in ("c", "rust", "go", "zig")}}
        suffixes = {"goose": "goose", "c": "c", "rust": "rs", "go": "go", "zig": "zig"}
        for name in sources:
            data["benchmark"][name] = {"build": [], "run": []}
        for index in range(6):
            for name, body in sources.items():
                source = work / f"{name}_{index}.{suffixes[name]}"
                source.write_text(f"// build round {index}\n" + body)
                binary = work / f"{name}-bin"
                commands = {
                    "goose": build(source, binary),
                    "c": [tools["clang"], "-std=c11", "-O3", source, "-o", binary],
                    "rust": [tools["rustc"], "-C", "opt-level=3", source, "-o", binary],
                    "go": [tools["go"], "build", "-o", binary, source],
                    "zig": [tools["zig"], "build-exe", source, "-O", "ReleaseFast", "-lc", "-fno-incremental", "--cache-dir", work / f"zig-cache-{index}", f"-femit-bin={binary}"],
                }
                result = checked(commands[name])
                if index:
                    data["benchmark"][name]["build"].append(result["seconds"])
                recorded = ["goose" if name == "goose" else Path(commands[name][0]).name] + commands[name][1:]
                data["benchmark"][name]["build_command"] = [norm(str(v)) for v in recorded]
                print(f"build {index} {name}: {result['seconds']:.4f}s", flush=True)
        for index in range(8):
            for name in sources:
                result = checked([work / f"{name}-bin"])
                if result["stdout"] != reference.EXPECTED:
                    raise RuntimeError(f"Wrong output for {name}: {result}")
                if index:
                    data["benchmark"][name]["run"].append(result["seconds"])
        for result in data["benchmark"].values():
            result["build"] = reference.summary(result["build"])
            result["run"] = reference.summary(result["run"])
            result["output"] = reference.EXPECTED
    args.output.write_text(json.dumps(data, indent=2) + "\n")
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
