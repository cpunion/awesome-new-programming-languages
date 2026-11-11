#!/usr/bin/env python3
"""Reproduce allocation-site and reuse checks; this is not a timing benchmark."""

import argparse
import datetime
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goose-bin", required=True, type=Path)
    parser.add_argument("--koka-bin", required=True, type=Path)
    parser.add_argument("--lean-toolchain", default="leanprover/lean4:v4.34.1")
    parser.add_argument("--output", type=Path, default=HERE / "results.json")
    args = parser.parse_args()
    args.goose_bin = args.goose_bin.resolve()
    args.koka_bin = args.koka_bin.resolve()
    clang = shutil.which("clang")
    if not clang or not shutil.which("elan"):
        raise RuntimeError("Clang and elan are required")
    if platform.system() != "Darwin":
        raise RuntimeError("This reproduction was validated on macOS; adapt native link flags for other hosts")
    data = {"measured_at": datetime.datetime.now().astimezone().isoformat(),
            "host": platform.system() + "/" + platform.machine(),
            "scope": "Source-level allocation sites and generated code, not process-wide allocation, RSS, performance, or a memory-safety proof",
            "tools": {}, "records": {}, "lean": {}, "koka": {}}
    with tempfile.TemporaryDirectory(prefix="memory-model-checks-") as directory:
        work = Path(directory)
        for source in HERE.iterdir():
            if source.suffix in (".c", ".h", ".lean", ".kk", ".goose"):
                shutil.copyfile(source, work / source.name)

        def run(command):
            p = subprocess.run([str(v) for v in command], cwd=work, capture_output=True, text=True, timeout=300)
            if p.returncode:
                raise RuntimeError(f"Command failed ({p.returncode}): {command}\n{p.stdout}\n{p.stderr}")
            return p.stdout.strip(), p.stderr.strip()

        def normalized(text):
            for original, replacement in ((str(work), "{work}"), (str(args.goose_bin), "{goose}"), (str(args.koka_bin), "{koka}")):
                text = text.replace(original, replacement)
            text = text.replace(str(work.resolve()), "{work}")
            return text

        data["tools"]["clang"] = run([clang, "--version"])[0].splitlines()[0]
        data["tools"]["goose"] = run([args.goose_bin, "version"])[0]
        data["tools"]["koka"] = run([args.koka_bin, "--version"])[0].splitlines()[0]
        lean = ["elan", "run", args.lean_toolchain]
        data["tools"]["lean"] = run(lean + ["lean", "--version"])[0]
        if "f4637bf" not in data["tools"]["goose"] or "3.2.9" not in data["tools"]["koka"]:
            raise RuntimeError("Expected Goose f4637bf and Koka 3.2.9")
        run([clang, "-std=c11", "-O2", "-c", "allocator_audit.c", "-o", "allocator_audit.o"])
        generated, diagnostics = run([args.goose_bin, "-o", "records.c", "records.goose", "--standalone", "--offline", "--stats"])
        data["records"]["goose_codegen"] = normalized(generated + "\n" + diagnostics)
        run([clang, "-std=c11", "-O2", "-include", "allocator_audit.h", "records.c", "allocator_audit.o", "-lm", "-lpthread", "-o", "records"])
        for name in ("records_individual", "records_region"):
            run([clang, "-std=c11", "-O2", name + ".c", "allocator_audit.o", "-o", name])
        for name in ("records", "records_individual", "records_region"):
            stdout, stderr = run([work / name])
            phases = [json.loads(line) for line in stderr.splitlines() if line.startswith("{")]
            expected = str(sum(i + len(f"row-{i}") + sum(f"row-{i}".encode()) for i in range(10000)))
            if stdout != expected or [p["phase"] for p in phases] != ["startup", "work"]:
                raise RuntimeError(f"Unexpected record check: {name}, {stdout}, {stderr}")
            data["records"][name] = {"checksum": stdout, "phases": phases}
        assert data["records"]["records"]["phases"][1]["malloc_calls"] == 0
        assert data["records"]["records_individual"]["phases"][1]["malloc_calls"] == 10001
        assert data["records"]["records_region"]["phases"][1]["malloc_calls"] == 1
        print("Goose/C record allocation checks passed", flush=True)

        run(lean + ["lean", "-c", "Reuse.c", "Reuse.lean"])
        native = lean + ["leanc", "-O2", "-mmacosx-version-min=15.0"]
        run(native + ["-c", "lean_audit.c", "-o", "lean_audit.o"])
        run(native + ["-include", "lean_audit.h", "-c", "Reuse.c", "-o", "Reuse.o"])
        run(native + ["Reuse.o", "lean_audit.o", "-o", "reuse"])
        stdout, stderr = run([work / "reuse"])
        observations = [json.loads(line) for line in stdout.splitlines()]
        assert [o["generated_ctor_calls"] for o in observations] == [0, 1000]
        assert [o["checksum"] for o in observations] == [500500, 500500]
        assert [o["original_checksum"] for o in observations] == [0, 499500]
        c = (work / "Reuse.c").read_text()
        begin = c.index("LEAN_EXPORT lean_object* l_transform(lean_object* v_")
        end = c.index("\nLEAN_EXPORT", begin + 1)
        data["lean"] = {"observations": observations, "transform_c": c[begin:end],
                        "stderr": normalized(stderr),
                        "scope": "Calls to lean_alloc_ctor in this generated C translation unit between audit markers; not allocations hidden in precompiled runtime or inline helpers"}
        assert "lean_is_exclusive" in data["lean"]["transform_c"]
        print("Lean unique/shared constructor checks passed", flush=True)

        for enabled in (True, False):
            tag = "on" if enabled else "off"
            command = [args.koka_bin, "-O2", f"--builddir=koka-build-{tag}", f"--outputdir=koka-out-{tag}", "-o", f"koka-{tag}", "reuseprobe.kk"]
            if not enabled:
                command.append("--fno-reuse")
            run(command)
            stdout, stderr = run([work / f"koka-{tag}"])
            assert stdout.splitlines() == ["501500", "501500", "500500"]
            c = (work / f"koka-out-{tag}" / "reuseprobe.c").read_text()
            begin = c.index("kk_std_core_types__list kk_reuseprobe__trmc_")
            end = c.index("\n}\n", begin) + 3
            fragment = c[begin:end]
            assert ("kk_datatype_ptr_reuse" in fragment) == enabled
            data["koka"][tag] = {"stdout": stdout, "stderr": normalized(stderr), "transform_c": fragment,
                                 "reuse_enabled": enabled, "scope": "Generated-code comparison and output preservation; no allocation counter or runtime ratio"}
        print("Koka reuse on/off code generation and outputs verified", flush=True)
        for name, expected in (("fipgood", "Just(3)"), ("fipbad", "Just(1)")):
            build_stdout, build_stderr = run([args.koka_bin, "-O2", "--builddir=koka-build-fip", "--outputdir=koka-out-fip", "-o", name, name + ".kk"])
            diagnostics = build_stdout + "\n" + build_stderr
            marker = "function allocates at most 1 but was declared as allocating nothing"
            assert (marker in diagnostics) == (name == "fipbad")
            stdout, stderr = run([work / name])
            assert stdout == expected
            data["koka"][name] = {"build_exit_code": 0, "stdout": stdout,
                "allocation_contract_warning": marker in diagnostics,
                "diagnostics": normalized("\n".join(line for line in diagnostics.splitlines() if "warning:" in line or marker in line))}
        print("Koka fip checks verified: violating declaration warns but builds", flush=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
