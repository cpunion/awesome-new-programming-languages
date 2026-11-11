#!/usr/bin/env python3
"""Probe the pinned Rune compiler, locally or in the documented Docker layout."""

import argparse
import datetime
import json
from pathlib import Path
import re
import subprocess
import tempfile

PIN = "a8fb12f974736f20eaefb1f614df68411dac7bc8"
PROBES = {
    "secret_branch": ('''password = secret(argv[1])
if password == "password" {
  println "leaked"
}
''', "compile_rejection", "secret"),
    "secret_index": ('''index = secret(1)
a = [1, 2, 3]
println a[index]
''', "compile_rejection", "indexing with a secret"),
    "changed_type": ('''a = 1
a = "wrong"
println a
''', "compile_rejection", "assigning different type"),
    "bounds": ('''a = [1, 2, 3]
println a[3]
''', "runtime_rejection", "indexed passed the end of an array"),
    "overflow": ('''x = 255u8
println x + 1u8
''', "runtime_rejection", "overflow"),
    "relationship": ('''class Root(self) {
  self.marker = 1u32
}
class Item(self, value: u32) {
  self.value = value
}

relation DoublyLinked Root Item cascade

root = Root()
root.appendItem(Item(7u32))
println root.firstItem!.value
root.firstItem!.destroy()
println isnull(root.firstItem)
''', "success", "7\ntrue"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--container", help="Docker container with the source at /work/rune and its parent mounted at /work")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results.json"))
    args = parser.parse_args()
    source = args.source.resolve()
    sha = subprocess.check_output(["git", "-C", source, "rev-parse", "HEAD"], text=True).strip()
    if sha != PIN:
        raise RuntimeError(f"Expected {PIN}, got {sha}")
    prefix = ["docker", "exec", "-w", "/work/rune", args.container] if args.container else []
    compiler = "/work/rune/rune" if args.container else str(source / "rune")

    def run(command):
        result = subprocess.run(prefix + [str(v) for v in command], cwd=source, capture_output=True, text=True, timeout=60)
        return {"exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}

    data = {"measured_at": datetime.datetime.now().astimezone().isoformat(), "source_commit": sha,
            "method": "Default safety enabled, -O passed to Rune; no performance comparison; sources retained in this script",
            "platform": run(["uname", "-sm"]), "clang": run(["clang", "--version"]), "probes": {}}
    with tempfile.TemporaryDirectory(prefix="rune-probes-", dir=source.parent) as directory:
        work = Path(directory)
        visible = Path("/work") / work.name if args.container else work
        for name, (body, expectation, marker) in PROBES.items():
            path = work / f"{name}.rn"
            path.write_text(body)
            compiled = run([compiler, "-O", "-l", visible / f"{name}.ll", visible / path.name])
            record = {"build": compiled, "expectation": expectation}
            if expectation == "compile_rejection":
                diagnostic = compiled["stdout"] + compiled["stderr"]
                record["matches_expectation"] = compiled["exit_code"] != 0 and "Error:" in diagnostic and marker in diagnostic.rsplit("Error:", 1)[-1].lower()
                if name == "secret_branch" and compiled["exit_code"] == 0:
                    record["unexpected_run"] = run([visible / name, "password"])
                    ir = work / f"{name}.ll"
                    functions = re.findall(r"define[^\n]*@secret_branch\([^\n]*\).*?\n\}", ir.read_text(), re.S)
                    if len(functions) != 1:
                        raise RuntimeError("Expected the secret_branch function in emitted LLVM IR")
                    record["ir_secret_branch"] = functions[0]
            elif compiled["exit_code"] == 0:
                executed = run([visible / name])
                record["run"] = executed
                if expectation == "success":
                    record["matches_expectation"] = executed["exit_code"] == 0 and executed["stdout"] == marker
                else:
                    record["matches_expectation"] = executed["exit_code"] != 0 and marker in (executed["stdout"] + executed["stderr"]).lower()
            else:
                record["matches_expectation"] = False
            data["probes"][name] = record
            print(f"{name}: {record['matches_expectation']}", flush=True)
        encoded = json.dumps(data, indent=2).replace(str(visible), "{work}").replace(str(work), "{work}").replace(str(source), "{source}").replace("/work/rune", "{source}")
    args.output.write_text(encoded + "\n")
    if not all(p["matches_expectation"] for p in data["probes"].values()):
        raise SystemExit("One or more observations differed from the stated expectation; inspect results.json")


if __name__ == "__main__":
    main()
