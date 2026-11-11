#!/usr/bin/env python3
"""Reproduce Gojo safety probes and compare a native integer loop with C/Rust/Go/Zig."""

import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


GOJO_COMMIT = "215e07c8f016203c52a68e91db9d7097e8e4ff4b"
REFERENCE = Path(__file__).resolve().parents[1] / "bend-2026-11-11/run.py"
SPEC = importlib.util.spec_from_file_location("integer_loop_reference", REFERENCE)
reference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reference)

GOJO_SOURCE = """fn main() {
    var x: u32 = 1
    for _ in 0..50000000 {
        x = x ^ (x << 13)
        x = x ^ (x >> 17)
        x = x ^ (x << 5)
    }
    println(x)
}
"""


def run(command, cwd, env, timeout=180):
    return reference.execute([str(part) for part in command], cwd, env, timeout)


def checked(command, cwd, env):
    result = run(command, cwd, env)
    reference.require_success(result, " ".join(str(part) for part in command))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gojo-source", required=True, type=Path)
    parser.add_argument("--gojo-bin", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results.json"))
    args = parser.parse_args()
    source = args.gojo_source.resolve()
    gojo = args.gojo_bin.resolve()
    env = dict(os.environ, GOJO_MAXPROCS="1")
    tools = {name: shutil.which(name) for name in ("clang", "rustc", "go", "zig", "git")}
    if not all(tools.values()):
        raise RuntimeError(f"Missing tools: {tools}")
    revision = checked([tools["git"], "rev-parse", "HEAD"], source, env)["stdout"]
    if revision != GOJO_COMMIT:
        raise RuntimeError(f"Expected {GOJO_COMMIT}, got {revision}")
    if checked([tools["git"], "status", "--porcelain"], source, env)["stdout"]:
        raise RuntimeError("Use an unmodified source checkout")
    data = {
        "measured_at": datetime.datetime.now().astimezone().isoformat(),
        "gojo_commit": GOJO_COMMIT,
        "gojo_version": checked([gojo, "version"], source, env)["stdout"],
        "tools": {},
        "method": {
            "build_runs": 5,
            "execution_runs": 7,
            "warmups": 1,
            "iterations": reference.ITERATIONS,
            "expected_output": reference.EXPECTED,
            "cache": "Fresh experiment cache; record first Gojo build separately, keep its compiled runtime warm, remove bin_* artifacts before each timed Gojo build; warm standard libraries; fresh source per build and Zig local cache per build",
            "timing": "Serial round-robin wall time including process start; Gojo release uses clang -O2, C -O3, Rust opt-level=3, Go default, Zig ReleaseFast; GOJO_MAXPROCS=1",
            "scope": "One integer loop; allocation, GPU, application workloads and large-project builds need separate measurements",
        },
        "probes": {},
        "benchmark": {},
    }
    for name in tools:
        flag = "version" if name in ("go", "zig") else "--version"
        data["tools"][name] = checked([tools[name], flag], source, env)["stdout"].splitlines()[0]
    for name in ("machdep.cpu.brand_string", "hw.memsize", "hw.ncpu"):
        data[name] = checked(["sysctl", "-n", name], source, env)["stdout"]

    with tempfile.TemporaryDirectory(prefix="gojo-research-") as directory:
        work = Path(directory)
        cache = work / "gojo-cache"
        env["GOJO_CACHE"] = str(cache)
        normalize = lambda text: text.replace(str(work), "{work}").replace(str(source), "{gojo}")
        negative = [
            "no_nil", "move_in_loop", "maybe_moved", "move_while_borrowed",
            "unhandled_result", "non_exhaustive", "task_race", "linear_leaks",
        ]
        for name in negative:
            file = source / "tests/errors" / f"{name}.gojo"
            expected = re.findall(r"// error: (.+)", file.read_text())
            result = run([gojo, "check", file], work, env)
            result["matches_expectation"] = (
                result["exit_code"] == 1
                and all(message in result["stderr"] for message in expected)
                and "internal error" not in result["stderr"]
            )
            result["stderr"] = normalize(result["stderr"])
            data["probes"][name] = result
            if not result["matches_expectation"]:
                raise RuntimeError(f"Unexpected result for {name}: {result}")
            print(f"probe {name}: pass", flush=True)

        for name in ("ownership", "lastuse", "linear", "drop_states"):
            file = source / "tests/run" / f"{name}.gojo"
            result = checked([gojo, "run", "--release", "--cc", tools["clang"], file], work, env)
            result["matches_expectation"] = result["stdout"] == file.with_suffix(".out").read_text().strip()
            result["stderr"] = normalize(result["stderr"])
            data["probes"][name] = result
            if not result["matches_expectation"]:
                raise RuntimeError(f"Unexpected output for {name}: {result}")
            print(f"probe {name}: pass", flush=True)

        for name in ("overflow", "bounds", "requires"):
            file = source / "tests/panic" / f"{name}.gojo"
            expected = re.findall(r"// panic: (.+)", file.read_text())
            result = run([gojo, "run", "--release", "--cc", tools["clang"], file], work, env)
            result["matches_expectation"] = result["exit_code"] == 2 and all(message in result["stderr"] for message in expected)
            result["stderr"] = normalize(result["stderr"])
            data["probes"][name] = result
            if not result["matches_expectation"]:
                raise RuntimeError(f"Unexpected panic for {name}: {result}")
            print(f"probe {name}: pass", flush=True)

        bce = source / "tests/run/bce.gojo"
        result = checked([gojo, "claims", bce, "--json"], work, env)
        data["bounds_claims"] = json.loads(normalize(result["stdout"]))

        # Each compiler receives the same dependency-chained xorshift32 workload.
        sources = {"gojo": GOJO_SOURCE}
        sources.update({name: reference.SOURCES[name] for name in ("c", "rust", "go", "zig")})
        suffixes = {"gojo": "gojo", "c": "c", "rust": "rs", "go": "go", "zig": "zig"}
        cold_cache = work / "cold-cache"
        cold_env = dict(env, GOJO_CACHE=str(cold_cache))
        cold_file = work / "cold.gojo"
        cold_file.write_text(GOJO_SOURCE)
        data["first_gojo_release_build"] = checked(
            [gojo, "build", "--release", "--cc", tools["clang"], cold_file, "-o", work / "cold-bin"], work, cold_env,
        )
        for name in sources:
            data["benchmark"][name] = {"build": [], "run": []}
        for index in range(6):
            for name, body in sources.items():
                file = work / f"{name}_{index}.{suffixes[name]}"
                file.write_text(f"// build round {index}\n" + body)
                binary = work / f"{name}-bin"
                for artifact in cache.glob("bin_*"):
                    artifact.unlink()
                commands = {
                    "gojo": [gojo, "build", "--release", "--cc", tools["clang"], file, "-o", binary],
                    "c": [tools["clang"], "-std=c11", "-O3", file, "-o", binary],
                    "rust": [tools["rustc"], "-C", "opt-level=3", file, "-o", binary],
                    "go": [tools["go"], "build", "-o", binary, file],
                    "zig": [tools["zig"], "build-exe", file, "-O", "ReleaseFast", "-lc", "-fno-incremental",
                            "--cache-dir", work / f"zig-cache-{index}", f"-femit-bin={binary}"],
                }
                result = checked(commands[name], work, env)
                if index:
                    data["benchmark"][name]["build"].append(result["seconds"])
                recorded = [name if name == "gojo" else Path(commands[name][0]).name] + commands[name][1:]
                data["benchmark"][name]["build_command"] = [normalize(str(value)) for value in recorded]
                print(f"build {index} {name}: {result['seconds']:.4f}s", flush=True)
        for index in range(8):
            for name in sources:
                result = checked([work / f"{name}-bin"], work, env)
                if result["stdout"] != reference.EXPECTED:
                    raise RuntimeError(f"Wrong checksum for {name}: {result}")
                if index:
                    data["benchmark"][name]["run"].append(result["seconds"])
                print(f"run {index} {name}: {result['seconds']:.4f}s", flush=True)
        for name, measurement in data["benchmark"].items():
            measurement["build"] = reference.summary(measurement["build"])
            measurement["run"] = reference.summary(measurement["run"])
            measurement["output"] = reference.EXPECTED

    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
