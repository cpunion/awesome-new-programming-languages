#!/usr/bin/env python3
"""Check Goose data-stack assignment and reference-lifetime boundaries."""

import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

REVISION = "f4637bfb342fb70d42bea0474eab9e62a3c99d68"
POSITIVE = {
    "simultaneous_containers": (3, "", """fn main() {
    var a: i64[>..] = [];
    var b: i64[>..] = [];
    var c: i64[>..] = [];
    a.push(1); b.push(2); c.push(3);
    assert(a[0] + b[0] + c[0] == 6);
}
"""),
    "sequential_blocks": (1, "", """fn main() {
    { var a: i64[>..] = []; a.push(1); assert(a[0] == 1); }
    { var b: i64[>..] = []; b.push(2); assert(b[0] == 2); }
    { var c: i64[>..] = []; c.push(3); assert(c[0] == 3); }
}
"""),
    "sequential_uses_same_block": (3, "", """fn main() {
    var a: i64[>..] = []; a.push(1); assert(a[0] == 1);
    var b: i64[>..] = []; b.push(2); assert(b[0] == 2);
    var c: i64[>..] = []; c.push(3); assert(c[0] == 3);
}
"""),
    "persistent_result_loop_scratch": (2, "", """fn main() {
    var result: i64[>..] = [];
    for round in 100 {
        var scratch: i64[>..] = [];
        for i in 10 { scratch.push(round + i); }
        result.push(scratch[0]);
    }
    var sum: i64 = 0;
    for x in result { sum += x; }
    assert(result.len == 100 && sum == 4950);
}
"""),
    "result_destination_and_callee_scratch": (2, "", """fn make() -> i64[>..] {
    var scratch: i64[>..] = [];
    for i in 10 { scratch.push(i); }
    return [scratch.len];
}
fn main() {
    var result: i64[>..] = make();
    assert(result[0] == 10);
}
"""),
    "clear_after_reference_last_use": (1, "", """fn main() {
    var xs: i64[>..] = [7];
    let first .= xs[0];
    assert(first == 7);
    xs.clear();
    assert(xs.len == 0);
}
"""),
}
NEGATIVE = {
    "escaping_view": ("does not outlive the destination", """fn main() {
    var outer: u8[>..] = [];
    var view = outer[..];
    { var inner: u8[>..] = [1, 2]; view = inner[..]; }
    print(view.len);
}
"""),
    "clear_before_reference_last_use": ("cannot clear xs while first is still used", """fn main() {
    var xs: i64[>..] = [7];
    let first .= xs[0];
    xs.clear();
    print(first);
}
"""),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goose-bin", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results.json"))
    args = parser.parse_args()
    goose = args.goose_bin.resolve()
    clang = shutil.which("clang")
    if clang is None:
        raise RuntimeError("Clang is required for native execution")
    data = {
        "measured_at": datetime.datetime.now().astimezone().isoformat(),
        "source_commit": REVISION,
        "host": platform.system() + "/" + platform.machine(),
        "scope": "Static data-stack report, native assertions, and checker diagnostics; no RSS, throughput, allocator-count, or complete safety measurement",
        "tools": {}, "positive": {}, "negative": {},
    }
    with tempfile.TemporaryDirectory(prefix="goose-stack-checks-") as directory:
        work = Path(directory)
        env = dict(os.environ, GOOSE_HOME=str(work / "goose-home"))

        def norm(value):
            for path in (str(work), str(work.resolve())):
                value = value.replace(path, "{work}")
            return value.replace(str(goose), "{goose}")

        def run(command, required=True):
            p = subprocess.run([str(v) for v in command], cwd=work, env=env,
                               text=True, capture_output=True, timeout=120)
            result = {"exit_code": p.returncode,
                      "stdout": norm(p.stdout.strip()), "stderr": norm(p.stderr.strip())}
            if required and p.returncode != 0:
                raise RuntimeError(result)
            return result

        data["tools"]["goose"] = run([goose, "version"])["stdout"]
        data["tools"]["clang"] = run([clang, "--version"])["stdout"].splitlines()[0]
        if REVISION[:7] not in data["tools"]["goose"]:
            raise RuntimeError("Expected Goose revision " + REVISION[:7])
        for name, (count, expected, source) in POSITIVE.items():
            path = work / (name + ".goose")
            path.write_text(source)
            build = run([goose, "build", path.name, "-O2", "--offline", "--stacks",
                         "--cc", clang, "-o", name])
            report = build["stdout"] + "\n" + build["stderr"]
            match = re.search(r"main program: (\d+) data stacks", report)
            if match is None or int(match.group(1)) != count:
                raise RuntimeError({"case": name, "expected_stacks": count, "build": build})
            execution = run([work / name])
            if execution["stdout"] != expected:
                raise RuntimeError({"case": name, "expected_output": expected, "execution": execution})
            data["positive"][name] = {"source": source, "data_stacks": count,
                                      "build": build, "execution": execution}
            print(f"{name}: {count} data stacks, native assertions passed", flush=True)
        for name, (marker, source) in NEGATIVE.items():
            path = work / (name + ".goose")
            path.write_text(source)
            result = run([goose, "check", path.name, "--offline"], required=False)
            if result["exit_code"] != 1 or marker not in result["stderr"]:
                raise RuntimeError({"case": name, "expected_diagnostic": marker, "result": result})
            data["negative"][name] = {"source": source, "diagnostic": result}
            print(f"{name}: expected rejection verified", flush=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print("Saved", args.output)


if __name__ == "__main__":
    main()
