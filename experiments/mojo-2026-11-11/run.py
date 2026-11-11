#!/usr/bin/env python3
"""Check Mojo ownership behavior and reproduce a five-language native integer loop."""

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
MOJO_SOURCE = """def main():
    var x: UInt32 = 1
    for _ in range(50000000):
        x = x ^ (x << 13)
        x = x ^ (x >> 17)
        x = x ^ (x << 5)
    print(x)
"""
PROBES = {
    "type_mismatch": ("def main():\n    var x: Int = \"wrong\"\n    print(x)\n", "cannot implicitly convert"),
    "immutable_argument": ("def change(xs: List[Int]):\n    xs.append(2)\n\ndef main():\n    var xs: List[Int] = [1]\n    change(xs)\n", "invalid use of mutating method"),
    "mutable_alias": ("def change(mut a: List[Int], mut b: List[Int]):\n    a.append(1)\n    b.append(2)\n\ndef main():\n    var xs: List[Int] = [0]\n    change(xs, xs)\n", "aliasing values passed mutably"),
    "use_after_transfer": ("def consume(var s: String):\n    print(s)\n\ndef main():\n    var s: String = \"owned\"\n    consume(s^)\n    print(s)\n", "use of uninitialized value"),
    "unhandled_error": ("def fail() raises -> Int:\n    raise Error(\"failed\")\n\ndef main():\n    print(fail())\n", "cannot call function that may raise"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mojo-bin", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results.json"))
    args = parser.parse_args()
    mojo = args.mojo_bin.absolute()
    env = dict(os.environ)
    tools = {name: shutil.which(name) for name in ("clang", "rustc", "go", "zig")}
    if not all(tools.values()):
        raise RuntimeError(f"Missing tools: {tools}")
    data = {
        "measured_at": datetime.datetime.now().astimezone().isoformat(),
        "tools": {}, "probes": {}, "benchmark": {},
        "method": {
            "build_runs": 5, "execution_runs": 7, "warmups": 1,
            "iterations": reference.ITERATIONS, "expected_output": reference.EXPECTED,
            "builds": "Serial round-robin builds; fresh source name and comment per build; warm toolchains, standard libraries, and filesystem; fresh Zig local cache with incremental compilation off",
            "optimization": "Mojo -O3, C -O3, Rust opt-level=3, Go defaults, Zig ReleaseFast",
            "scope": "One native CPU scalar loop including process start and printing; GPU, allocation and large-project builds require separate measurements",
        },
    }
    def run(command, cwd):
        return reference.execute([str(part) for part in command], cwd, env)
    def checked(command, cwd):
        result = run(command, cwd)
        reference.require_success(result, str(command))
        return result
    version = checked([mojo, "--version"], Path.cwd())
    data["tools"]["mojo"] = version["stdout"]
    if not version["stdout"].startswith("Mojo 1.2.0 "):
        raise RuntimeError(f"Expected Mojo 1.2.0, got {version['stdout']}")
    for name in tools:
        flag = "version" if name in ("go", "zig") else "--version"
        data["tools"][name] = checked([tools[name], flag], Path.cwd())["stdout"].splitlines()[0]
    for name in ("machdep.cpu.brand_string", "hw.memsize", "hw.ncpu"):
        data[name] = checked(["sysctl", "-n", name], Path.cwd())["stdout"]
    with tempfile.TemporaryDirectory(prefix="mojo-research-") as directory:
        work = Path(directory)
        def normalize(text):
            return text.replace(str(mojo), "{mojo}").replace(str(work), "{work}")
        for name, (body, diagnostic) in PROBES.items():
            source = work / f"{name}.mojo"
            source.write_text(body)
            result = run([mojo, "build", source, "-o", work / name], work)
            result["matches_expectation"] = result["exit_code"] == 1 and diagnostic in result["stderr"]
            result["stderr"] = normalize(result["stderr"])
            data["probes"][name] = result
            if not result["matches_expectation"]:
                raise RuntimeError(f"Unexpected probe {name}: {result}")
            print(f"probe {name}: pass", flush=True)
        source = work / "comptime.mojo"
        source.write_text("comptime N = 6 * 7\n\ndef main():\n    print(N)\n")
        compiled = checked([mojo, "build", source, "-o", work / "comptime"], work)
        result = checked([work / "comptime"], work)
        result["matches_expectation"] = result["stdout"] == "42"
        if not result["matches_expectation"]:
            raise RuntimeError(f"Unexpected comptime output: {result}")
        result["build_stderr"] = normalize(compiled["stderr"])
        data["probes"]["comptime"] = result
        sources = {"mojo": MOJO_SOURCE, **{name: reference.SOURCES[name] for name in ("c", "rust", "go", "zig")}}
        suffixes = {"mojo": "mojo", "c": "c", "rust": "rs", "go": "go", "zig": "zig"}
        for name in sources:
            data["benchmark"][name] = {"build": [], "run": []}
        for index in range(6):
            for name, body in sources.items():
                source = work / f"{name}_{index}.{suffixes[name]}"
                comment = "#" if name == "mojo" else "//"
                source.write_text(f"{comment} build round {index}\n" + body)
                binary = work / f"{name}-bin"
                commands = {
                    "mojo": [mojo, "build", "-O3", source, "-o", binary],
                    "c": [tools["clang"], "-std=c11", "-O3", source, "-o", binary],
                    "rust": [tools["rustc"], "-C", "opt-level=3", source, "-o", binary],
                    "go": [tools["go"], "build", "-o", binary, source],
                    "zig": [tools["zig"], "build-exe", source, "-O", "ReleaseFast", "-lc", "-fno-incremental", "--cache-dir", work / f"zig-cache-{index}", f"-femit-bin={binary}"],
                }
                result = checked(commands[name], work)
                if index:
                    data["benchmark"][name]["build"].append(result["seconds"])
                recorded = [name if name == "mojo" else Path(commands[name][0]).name] + commands[name][1:]
                data["benchmark"][name]["build_command"] = [normalize(str(value)) for value in recorded]
                data["benchmark"][name]["build_stderr"] = normalize(result["stderr"])
                print(f"build {index} {name}: {result['seconds']:.4f}s", flush=True)
        for index in range(8):
            for name in sources:
                result = checked([work / f"{name}-bin"], work)
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
