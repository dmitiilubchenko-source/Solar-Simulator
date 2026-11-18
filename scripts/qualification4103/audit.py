"""Recalculate admission evidence from real Job receipts, logs and frozen inputs."""
import ast
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from . import monitor as m
from .consumer import require_completion

RAW = Path("C:/Users/Admin/Documents/Codex/Solar4103-raw")
BASE = "a5f85b2f25fa46cc756126a5ec6efc4715841705"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MONITOR_SHA = hashlib.sha256((HERE / "monitor.py").read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gone(pid, birth):
    try:
        handle = m.process_handle(pid)
    except OSError as exc:
        if exc.winerror == 87:
            return True
        raise
    try:
        return m.identity(handle)[0] != birth or m.wait(handle, 0) == 0
    finally:
        m.checked(m.close(handle))


def audit():
    # Offsets and sizes from the Win64 SDK field order, including trailing padding.
    assert ctypes.sizeof(m.Basic) == 48
    assert [getattr(m.Basic, k).offset for k in ("user","kernel","total","active","terminated")] == [0,8,36,40,44]
    assert [ctypes.sizeof(t) for t in (m.Process,m.Startup,m.StartupEx,m.Extended)] == [24,104,112,144]
    for file in HERE.glob("*.py"):
        ast.parse(file.read_bytes(), filename=str(file))
    diff = subprocess.check_output(["git", "-C", str(ROOT), "diff", BASE, "--",
        "scripts/check_portable.py", "src", "rust", "pyproject.toml", "scripts/qualification409",
        "scripts/qualification4095", "scripts/qualification410", "scripts/qualification4101",
        "scripts/qualification4102"])
    assert not diff
    archive = Path(read(ROOT/"scripts/qualification410/execution-plan.json")["bindings"]["archive"]["archive"])
    assert digest(archive) == "33114f5ac2234e01e1e248fae757187a50a81020e2b225ee6b746e28e1073e33"
    with zipfile.ZipFile(archive) as z:
        native = [n for n in z.namelist() if "/solar_native/" in n and n.endswith(".pyd")]
        assert len(native) == 1
        native_sha = hashlib.sha256(z.read(native[0])).hexdigest()
        assert native_sha == "a2b7e07573720a269efc712ee4fb74dcc747d24a4967d72d4c3d812158b3399b"
    portable = Path(read(ROOT/"scripts/qualification410/execution-plan.json")["bindings"]["acceptance_tool"]["path"])
    assert digest(portable) == "e332fca075e4dd686c3011a0f644c19e2af2210025badffb8117f516d74687a7"

    cases = {}
    identities = set()
    job_cpu = parent_cpu = visible_wall = 0
    current_differences = []
    expected = {
        "normal":None,"wrapper-help":None,"wrapper-child":None,"joined":None,
        "parent":"unexpected-owned-descendant","grand":"unexpected-owned-descendant",
        "enum-race":None,"cleanup-race":"unexpected-owned-descendant",
        "nonzero":"root-nonzero","crash":"root-nonzero","cpu":"stage-CPU","memory":"private-memory",
        "wall":"stage-wall","disk":"stage-disk","create":"monitor-error","assign":"monitor-error",
        "resume":"monitor-error","cleanup":"unexpected-owned-descendant","breakaway":None,
        "nested":None,"nested-restricted":None,"foreign":"monitor-error","loss":"root-nonzero",
        "loss-suspended":"root-nonzero","benchmark":None,"final-only":"final-accounting-unresolved",
        "close":"close-unresolved","write":"write-error"}
    for batch in ("atomic", "atomic-complement"):
        selection = read(RAW / batch / "selection.json")
        assert selection["source"] == MONITOR_SHA
        assert selection["fixture"] == digest(HERE/"fixture.py")
        assert selection["harness"] == digest(HERE/"regression.py")
        for name in selection["cases"]:
            folder = RAW / batch / (name + " output Юникод")
            case = read(folder / "result.json")
            path = folder / "guard/supervisor.json"
            parent_cpu += case["supervisor_CPU"] + case["signals"].get("file_setup_CPU", 0)
            visible_wall += case["elapsed"] + case["signals"].get("file_setup_wall", 0)
            if name == "write":
                assert not path.exists() and case["external_errors"][0]["type"] == "FileExistsError"
                assert (folder/"guard/supervisor.json.partial").read_bytes() == b"fixture write conflict"
                cases[name] = dict(reason="write-error", receipt=None)
                continue
            record = read(path)
            assert record["monitor_SHA256"] == MONITOR_SHA and record["limit_reason"] == expected[name]
            assert record["complete"] is (expected[name] is None)
            if record["complete"]:
                require_completion(path.parent, MONITOR_SHA)
            sequence = [point for pair in record["post_termination_snapshots"]
                        for point in (pair["job_before"],pair["job_after"])]
            final = record["final_job"]
            if final:
                sequence.append(final)
                assert record["worker_CPU_seconds"] == (final["user_100ns"]+final["kernel_100ns"])/1e7
                assert final["active"] == 0
                job_cpu += record["worker_CPU_seconds"]
                counted = sum(proc["final_CPU_seconds"] for proc in record["processes"])
                current_differences.append(dict(case=name, job=record["worker_CPU_seconds"],
                    handles=counted, sampled=len(record["processes"]), total=final["total"]))
            for key in ("user_100ns", "kernel_100ns", "snapshot_perf"):
                values = [sample[key] for sample in sequence]
                assert values == sorted(values) and all(x>=0 for x in values)
            for proc in record["processes"]:
                assert proc["job_membership_confirmed"] and proc["times"]["exit_FILETIME"] > 0
                identities.add((proc["pid"],proc["creation_FILETIME"]))
            if name == "final-only":
                assert final is None and record["worker_CPU_seconds"] is None and record["exit_code"] == 0
                assert case["signals"]["pre_fault_job"]["active"] == 0
                assert record["phases"].count("final-authoritative") == 1 <= record["phases"].count("post-cleanup")
                assert record["phases"].index("post-cleanup") < record["phases"].index("final-authoritative")
            if name in ("loss", "loss-suspended"):
                assert record["exit_code"] == 23 and not record["cleanup_performed"]
                assert not (folder/"inner/supervisor.json").exists()
                for proc in read(folder/"loss-members.json"):
                    identities.add((proc["pid"],proc["birth"]))
            if name == "breakaway":
                assert case["signals"]["breakaway_still_in_job"] is True
            if name == "foreign":
                assert case["signals"]["foreign_alive"] and any("belongs" in e["message"] for e in record["error"])
            if name == "grand":
                assert record["cleanup_performed"] and final["total"] > len(record["processes"])
            if name in ("enum-race", "cleanup-race"):
                identities.add(tuple(next(iter(case["signals"].values()))))
            if name in ("normal", "wrapper-child"):
                lines = (path.parent/"stdout.log").read_text(encoding="utf8").splitlines()
                args = next(json.loads(line) for line in lines if line.startswith('{"args":'))
                assert args["args"] == ["Русский пробел", 'quote"arg', "ends\\"]
                assert Path(args["cwd"]) == folder and args["stdin"] == "" and "stderr Юникод" in lines
                assert args["env"] == dict(PYTHONPATH=None,PYTHONHOME=None,OMP_NUM_THREADS="1",
                                          MKL_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1")
            cases[name] = dict(reason=record["limit_reason"], receipt_sha=digest(path))

    assert set(cases) == set(expected)
    assert all(gone(pid, birth) for pid, birth in identities)
    normal = read(next((RAW/"atomic").glob("normal */guard/supervisor.json")))
    negatives = {}
    with tempfile.TemporaryDirectory(dir=RAW) as tmp:
        p = Path(tmp)/"supervisor.json"
        for name in ("missing","invalid","noCPU","wrongSHA","jobAlive","counterMismatch"):
            if name == "invalid":
                p.write_bytes(b"{not valid")
            elif name != "missing":
                r = json.loads(json.dumps(normal))
                if name == "noCPU":r["worker_CPU_seconds"] = None
                if name == "wrongSHA":r["monitor_SHA256"] = "0"*64
                if name == "jobAlive":r["final_job"]["active"] = 1
                if name == "counterMismatch":r["worker_CPU_seconds"] += 1
                p.write_text(json.dumps(r),encoding="utf8")
            try:require_completion(p.parent,MONITOR_SHA)
            except (OSError,ValueError,KeyError,TypeError):negatives[name] = True
            else:raise AssertionError(name)

    old = read(ROOT/"scripts/qualification4102/independent-audit.json")
    old1 = read(ROOT/"scripts/qualification4101/independent-audit.json")["CPU_discrepancies"]
    earlier_cpu = earlier_wall = 0
    for directory in ("targeted","targeted-followup","nested-target","final"):
        for path in (RAW/directory).glob("*/guard/supervisor.json"):
            record = read(path)
            earlier_cpu += (record["worker_CPU_seconds"] or 0)
        for path in (RAW/directory).glob("*/result.json"):
            row = read(path)
            earlier_cpu += row["supervisor_CPU"] + row["signals"].get("file_setup_CPU",0)
            earlier_wall += row["elapsed"] + row["signals"].get("file_setup_wall",0)
    bench = read(next((RAW/"atomic-complement").glob("benchmark */result.json")))
    guard = read(next((RAW/"atomic-complement").glob("benchmark */guard/supervisor.json")))
    resource = dict(worker_cpu=job_cpu, supervisor_and_fixture_setup_cpu=parent_cpu, active_wall=visible_wall,
                    earlier_visible_cpu=earlier_cpu,earlier_visible_wall=earlier_wall,
                    missing_attempt_allowance=[8,15], review_prepare_backup_closure_allowance=[54,195],
                    charged_cpu=job_cpu+parent_cpu+earlier_cpu+62, charged_wall=visible_wall+earlier_wall+210,
                    peak_fixture_private=max(read(p)["peak_private_tree_sampled"] for p in RAW.glob("atomic*/*/guard/supervisor.json")),
                    full_stage_peak_unknown=True)
    assert resource["charged_cpu"] < 120 and resource["charged_wall"] < 360
    return dict(cases=cases, identities_checked=len(identities), consumer_negatives=negatives,
                native_sha=native_sha, portable_sha=digest(archive), monitor_sha=MONITOR_SHA,
                old_CPU_differences={"410.1":old1,"410.2":old["CPU_differences"]},
                CPU_differences=current_differences, resources=resource,
                benchmark=dict(files=14000,job_CPU=guard["worker_CPU_seconds"],
                    parent_CPU_before_receipt=guard["parent_supervision_CPU_seconds"],
                    parent_CPU_through_receipt=bench["supervisor_CPU"],wall=bench["elapsed"],
                    samples=guard["samples"]))


if __name__ == "__main__":
    result = audit()
    m.save(RAW/"independent-audit.json",result)
    print(json.dumps({k:result[k] for k in ("identities_checked","resources","benchmark")}))
