#!/usr/bin/env python3
"""Reproduce the Bend probes and a five-language xorshift32 microbenchmark."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import tempfile
import time


BEND_COMMIT = "d18110b6d6e9a70bb8814b2a8d8db092e301e540"
ITERATIONS = 50_000_000
EXPECTED = "376378803"
BUILD_RUNS = 5
EXECUTION_RUNS = 7

# Fixed-size, dependency-chained integer work. Every operation wraps at 32 bits.
SOURCES = {
    "bend": """import Base

def hash(n: Nat, +x: U32) -> U32:
  match n:
    case 0n:
      x
    case 1n+p:
      +b = U32.xor(x, U32.shln(x, 13n))
      +d = U32.xor(b, U32.shrn(b, 17n))
      hash(p, U32.xor(d, U32.shln(d, 5n)))

def main() -> IO(Unit):
  IO.print(U32.show(hash(50000000n, 1)))
""",
    "c": """#include <stdint.h>
#include <stdio.h>

int main(void) {
  uint32_t x = 1;
  for (uint64_t n = 0; n < 50000000; ++n) {
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
  }
  printf("%u\\n", x);
  return 0;
}
""",
    "rust": """fn main() {
    let mut x: u32 = 1;
    for _ in 0..50_000_000u64 {
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
    }
    println!("{}", x);
}
""",
    "go": """package main

import "fmt"

func main() {
    x := uint32(1)
    for n := uint64(0); n < 50000000; n++ {
        x ^= x << 13
        x ^= x >> 17
        x ^= x << 5
    }
    fmt.Println(x)
}
""",
    "zig": """extern "c" fn printf(format: [*:0]const u8, ...) c_int;

pub export fn main() c_int {
    var x: u32 = 1;
    var n: u64 = 0;
    while (n < 50_000_000) : (n += 1) {
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
    }
    _ = printf("%u\\n", x);
    return 0;
}
""",
}

# Each rejection checks a diagnostic fragment as well as the exit status.
PROBES = {
    "true_law": {
        "source": """import Base
law identity:
  for x: Nat
  {x == x : Nat}
def identity(x):
  {==}
""",
        "status": 0,
        "contains": "ALL PROOFS CHECK",
    },
    "inductive_law": {
        "source": """import Base
def count(n: Nat) -> Nat:
  match n:
    case 0n:
      0n
    case 1n+p:
      1n+count(p)

law count_identity:
  for n: Nat
  {count(n) == n : Nat}

def count_identity(n):
  match n:
    case 0n:
      {==}
    case 1n+p:
      %count_identity(p) : {1n+count(p) == 1n+_ : Nat}
      {==}
""",
        "status": 0,
        "contains": "ALL PROOFS CHECK",
    },
    "false_law": {
        "source": """import Base
law false_claim:
  {0n == 1n : Nat}
def false_claim():
  {==}
""",
        "status": 1,
        "contains": "SOME PROOFS FAIL",
    },
    "open_law": {
        "source": """import Base
law unfinished:
  {0n == 0n : Nat}
""",
        "status": 1,
        "contains": "SOME PROOFS FAIL",
    },
    "reuse_array": {
        "source": """import Base
def duplicate(a: Array<U32>) -> Array<U32> & Array<U32>:
  (a, a)
""",
        "status": 1,
        "contains": "consumed more than once",
    },
    "reuse_closure": {
        "source": """import Base
def twice(f: U32 -> U32, x: U32) -> U32:
  f(f(x))
""",
        "status": 1,
        "contains": "consumed more than once",
    },
    "type_mismatch": {
        "source": """import Base
def bad() -> U32:
  True{}
""",
        "status": 1,
        "contains": "SOME PROOFS FAIL",
    },
    "incomplete_match": {
        "source": """import Base
def bad(x: Bool) -> U32:
  match x:
    case True{}:
      1
""",
        "status": 1,
        "contains": "doesn't cover False",
    },
    "nondecreasing_recursion": {
        "source": """import Base
def loop(n: Nat) -> Nat:
  loop(n)
""",
        "status": 1,
        "contains": "SOME PROOFS FAIL",
    },
    "unsafe_recursion": {
        "source": """import Base
@unsafe
def loop(n: Nat) -> Nat:
  loop(n)
""",
        "status": 1,
        "contains": "relies on unsafe or foreign code",
    },
    "array_wrap": {
        "source": """import Base
def finish(r: Array<U32> & U32) -> IO(Unit):
  (a, x) = r
  IO.print(U32.show(x))

def main() -> IO(Unit):
  a = [0 : U32*8n]
  a[1] <- 42
  finish(a[9])
""",
        "status": 0,
        "contains": "42",
        "native": True,
    },
}


def execute(command, cwd, env, timeout=180):
    started = time.perf_counter()
    completed = subprocess.run(
        command, cwd=cwd, env=env, text=True, capture_output=True,
        timeout=timeout, check=False,
    )
    return {
        "seconds": time.perf_counter() - started,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def require_success(result, label):
    if result["exit_code"] != 0:
        raise RuntimeError(f"{label} failed\n{json.dumps(result, indent=2)}")


def summary(samples):
    return {
        "samples_seconds": samples,
        "median_seconds": statistics.median(samples),
        "min_seconds": min(samples),
        "max_seconds": max(samples),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bend-source", required=True, type=Path)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("results.json"))
    parser.add_argument("--lean-bin", type=Path,
                        help="Optional directory containing an installed lean and leanc")
    args = parser.parse_args()
    bend_source = args.bend_source.resolve()
    env = dict(os.environ)
    # Avoid a network version check at the end of each Bend command.
    env["BEND_ORIGIN"] = "http://127.0.0.1:1"
    env["BENDRTS"] = ""
    tools = {name: shutil.which(name) for name in
             ("bun", "clang", "rustc", "go", "zig", "git")}
    if not all(tools.values()):
        raise RuntimeError(f"Missing required tool: {tools}")
    revision = execute([tools["git"], "rev-parse", "HEAD"], bend_source, env)
    require_success(revision, "git rev-parse")
    if revision["stdout"] != BEND_COMMIT:
        raise RuntimeError(f"Expected Bend {BEND_COMMIT}, got {revision['stdout']}")
    dirty = execute([tools["git"], "status", "--porcelain"], bend_source, env)
    require_success(dirty, "git status")
    if dirty["stdout"]:
        raise RuntimeError("Use an unmodified Bend checkout for these measurements")

    bend = [tools["bun"], "--no-env-file", "--no-config",
            str(bend_source / "bend2/main.ts")]
    results = {
        "measured_at": datetime.datetime.now().astimezone().isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "bend_commit": BEND_COMMIT,
        "iterations": ITERATIONS,
        "expected_output": EXPECTED,
        "tools": {},
        "method": {
            "build_runs": BUILD_RUNS,
            "execution_runs": EXECUTION_RUNS,
            "warmups": 1,
            "build_cache": "Warm standard libraries and filesystem; a fresh source filename and comment per build, fresh Zig local cache per build; no application incremental state",
            "execution": "Serial round-robin runs, wall time including process start and output; Bend CPU threads=1, GPU=off",
            "bend_entry": "Bun source CLI, including checking, C emission and clang -O3 linking",
            "scope": "One fixed-seed integer loop; no application, allocation, memory, concurrency or GPU benchmark",
            "tool_paths": "Command names are recorded without absolute executable paths",
        },
        "probes": {},
        "benchmark": {},
    }
    for name in tools:
        flag = "version" if name in ("go", "zig") else "--version"
        version = execute([tools[name], flag], bend_source, env)
        require_success(version, f"{name} version")
        results["tools"][name] = {
            "executable": name, "version": version["stdout"].splitlines()[0],
        }
    results["tools"]["bend"] = execute(bend + ["version"], bend_source, env)["stdout"]
    for name in ("machdep.cpu.brand_string", "hw.memsize", "hw.ncpu"):
        value = execute(["sysctl", "-n", name], bend_source, env)
        require_success(value, f"sysctl {name}")
        results[name] = value["stdout"]

    with tempfile.TemporaryDirectory(prefix="bend-research-") as directory:
        work = Path(directory)
        for name, probe in PROBES.items():
            source = work / f"{name}.bend"
            source.write_text(probe["source"])
            command = bend + [str(source), "--check-only"]
            if probe.get("native"):
                binary = work / name
                built = execute(bend + [str(source), "-o", str(binary)], work, env)
                require_success(built, name)
                command = [str(binary), "+RTS", "--threads", "1", "--gpu", "off"]
            result = execute(command, work, env)
            result["matches_expectation"] = (
                result["exit_code"] == probe["status"]
                and probe["contains"] in (result["stdout"] + result["stderr"])
            )
            # Stable artifact paths make the diagnostics easier to compare.
            result["stdout"] = result["stdout"].replace(str(work), "{work}")
            result["stderr"] = result["stderr"].replace(str(work), "{work}")
            results["probes"][name] = result
            if not result["matches_expectation"]:
                raise RuntimeError(f"Unexpected probe result: {name}\n{result}")
            print(f"probe {name}: pass", flush=True)

        suffixes = {"bend": "bend", "c": "c", "rust": "rs", "go": "go", "zig": "zig"}
        for name in SOURCES:
            results["benchmark"][name] = {"build": [], "run": []}
        for round_index in range(BUILD_RUNS + 1):
            for name, body in SOURCES.items():
                source = work / f"{name}_{round_index}.{suffixes[name]}"
                comment = "#" if name == "bend" else "//"
                source.write_text(f"{comment} build round {round_index}\n" + body)
                binary = work / f"{name}_bin"
                commands = {
                    "bend": bend + [str(source), "-o", str(binary)],
                    "c": [tools["clang"], "-std=c11", "-O3", str(source), "-o", str(binary)],
                    "rust": [tools["rustc"], "-C", "opt-level=3", str(source), "-o", str(binary)],
                    "go": [tools["go"], "build", "-o", str(binary), str(source)],
                    "zig": [tools["zig"], "build-exe", str(source), "-O", "ReleaseFast", "-lc",
                            "-fno-incremental", "--cache-dir", str(work / f"zig_cache_{round_index}"),
                            f"-femit-bin={binary}"],
                }
                result = execute(commands[name], work, env)
                require_success(result, f"{name} build round {round_index}")
                if round_index > 0:
                    results["benchmark"][name]["build"].append(result["seconds"])
                recorded_command = [Path(commands[name][0]).name] + commands[name][1:]
                results["benchmark"][name]["build_command"] = [
                    value.replace(str(work), "{work}").replace(str(bend_source), "{bend}")
                    for value in recorded_command
                ]
                print(f"build {round_index} {name}: {result['seconds']:.4f}s", flush=True)

        for round_index in range(EXECUTION_RUNS + 1):
            for name in SOURCES:
                command = [str(work / f"{name}_bin")]
                if name == "bend":
                    command += ["+RTS", "--threads", "1", "--gpu", "off"]
                result = execute(command, work, env)
                require_success(result, f"{name} run round {round_index}")
                if result["stdout"] != EXPECTED:
                    raise RuntimeError(f"Wrong checksum: {name}: {result}")
                if round_index > 0:
                    results["benchmark"][name]["run"].append(result["seconds"])
                print(f"run {round_index} {name}: {result['seconds']:.4f}s", flush=True)

        for name, measurements in results["benchmark"].items():
            measurements["build"] = summary(measurements["build"])
            measurements["run"] = summary(measurements["run"])
            measurements["output"] = EXPECTED
            measurements["binary_bytes"] = (work / f"{name}_bin").stat().st_size

        results["kernel"] = {"status": "not_requested"}
        if args.lean_bin:
            lean = args.lean_bin.resolve() / "lean"
            leanc = args.lean_bin.resolve() / "leanc"
            version = execute([str(lean), "--version"], work, env)
            require_success(version, "Lean version")
            kernel_source = bend_source / "bend2/bendtt.lean"
            shutil.copyfile(kernel_source, work / "bendtt.lean")
            checked = execute([str(lean), "-c", "bendtt.c", "bendtt.lean"], work, env)
            require_success(checked, "BendTT Lean checking and C emission")
            built = execute([str(leanc), "-O3", "-DNDEBUG", "bendtt.c", "-o", "bendtt"], work, env)
            require_success(built, "BendTT native build")
            kernel_env = dict(env, BENDTT=str(work / "bendtt"))
            results["kernel"] = {
                "status": "built_and_checked",
                "lean_version": version["stdout"],
                "source_sha256": hashlib.sha256(kernel_source.read_bytes()).hexdigest(),
                "lean_check": checked,
                "native_build": built,
                "probes": {},
            }
            for name, probe in PROBES.items():
                if probe.get("native"):
                    continue
                result = execute(bend + [str(work / f"{name}.bend"), "--verdict"], work, kernel_env)
                result["matches_expectation"] = (
                    result["exit_code"] == probe["status"]
                    and probe["contains"] in (result["stdout"] + result["stderr"])
                )
                result["stdout"] = result["stdout"].replace(str(work), "{work}")
                result["stderr"] = result["stderr"].replace(str(work), "{work}")
                results["kernel"]["probes"][name] = result
                if not result["matches_expectation"]:
                    raise RuntimeError(f"Unexpected kernel probe result: {name}\n{result}")
                print(f"verdict {name}: pass", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    print(f"saved {args.output.resolve()}")


if __name__ == "__main__":
    main()
