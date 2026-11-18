"""Run the sealed fixture cases. Every worker is bounded and independent of Solar."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from . import monitor as m
from .consumer import require_completion

HERE = Path(__file__).resolve().parent
RAW = Path("C:/Users/Admin/Documents/Codex/Solar4103-raw")
WRAPPER = Path("C:/Users/Admin/Desktop/Solar-packaging-040-4095/scripts/check_portable.py")
WRAPPER_SHA = "e332fca075e4dd686c3011a0f644c19e2af2210025badffb8117f516d74687a7"
FIXTURE = HERE / "fixture.py"
PYTHON = "C:/Users/Admin/Documents/Codex/Solar407V-20261111/env/Scripts/python.exe"
DEFAULT_LIMITS = dict(cpu_seconds=9, wall_seconds=9, private_bytes=512*1024**2, disk_bytes=16*1024**2)
MODULE = "scripts.qualification4103.regression"
ROOT = HERE.parents[1]

CASES = {
    "final-only": ("argv", "final-accounting-unresolved"),
    "close": ("argv", "close-unresolved"),
    "write": ("argv", "write-error"),
    "wrapper-help": ("argv", None),
    "wrapper-child": ("argv", None),
    "normal": ("argv", None),
    "parent": ("parent", "unexpected-owned-descendant"),
    "grand": ("grand", "unexpected-owned-descendant"),
    "joined": ("joined", None),
    "enum-race": ("parent", None),
    "cleanup-race": ("parent", "unexpected-owned-descendant"),
    "nonzero": ("nonzero", "root-nonzero"),
    "crash": ("crash", "root-nonzero"),
    "cpu": ("burn", "stage-CPU"),
    "memory": ("sleep", "private-memory"),
    "wall": ("sleep", "stage-wall"),
    "disk": ("disk", "stage-disk"),
    "create": ("argv", "monitor-error"),
    "assign": ("argv", "monitor-error"),
    "resume": ("argv", "monitor-error"),
    "cleanup": ("parent", "unexpected-owned-descendant"),
    "breakaway": ("breakaway", None),
    "nested": ("argv", None),
    "nested-restricted": ("argv", None),
    "foreign": ("argv", "monitor-error"),
    "loss": ("argv", "root-nonzero"),
    "loss-suspended": ("argv", "root-nonzero"),
    "benchmark": ("sleep", None),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def release_child(folder):
    candidates = [int(p.stem) for p in folder.glob("*.started")]
    parent = int((folder / "parent.child").read_text())
    if parent not in candidates:
        return None
    handle = m.process_handle(parent)
    try:
        birth, _ = m.identity(handle)
        (folder / "release").touch()
        assert m.wait(handle, 1500) == 0
    finally:
        m.checked(m.close(handle))
    return [parent, birth]


def nested(folder, restricted=False):
    record = m.monitor([PYTHON, "-X", "utf8", "-I", "-B", str(FIXTURE), "argv", str(folder)],
                       folder / "nested-child", folder, DEFAULT_LIMITS, cwd=folder)
    if restricted:
        if record["complete"]:
            print("UI-limited outer Job still allowed child Job on this host", flush=True)
        else:
            assert any(e["type"] == "PermissionError" for e in record["error"])
            assert not list(folder.glob("*.started"))
    else:
        require_completion(folder / "nested-child", sha(Path(m.__file__)))


def run_case(name, folder, pin):
    folder.mkdir()
    mode, reason = CASES[name]
    params = DEFAULT_LIMITS.copy()
    limits = {"cpu": ("cpu_seconds", .14), "wall": ("wall_seconds", .3),
              "memory": ("private_bytes", 4096), "disk": ("disk_bytes", 1000)}
    if name in limits:
        key, value = limits[name]
        params[key] = value
    command = [PYTHON, "-X", "utf8", "-I", "-B", str(FIXTURE), mode, str(folder),
               "Русский пробел", 'quote"arg', "ends\\"]
    env = dict(os.environ, PYTHONPATH="ignored", PYTHONHOME="ignored")
    signals, errors = {}, []
    fault, substitute = None, None
    if name in ("create", "assign", "resume", "final-only", "cleanup"):
        fault = {"final-only": "authoritative_accounting", "cleanup": "terminate_job",
                 "assign": "is_in_job"}.get(name, name)
        def substitute(*args):
            signals["injection"] = fault
            if name == "final-only":
                status = m.accounting(args[0])
                signals["pre_fault_job"] = status
                assert status["active"] == 0 and status["total"] > 0
            raise OSError("forced " + fault)
    if name == "wrapper-help":
        assert sha(WRAPPER) == WRAPPER_SHA
        command = [PYTHON, "-X", "utf8", "-I", "-B", str(WRAPPER), "--help"]
    if name == "wrapper-child":
        # Import the exact wrapper. Exercise its subprocess.run module and the cwd/env/argv
        # shape used by check_gui. Never call an acceptance check or main().
        code = ("import importlib.util,sys; "
                "s=importlib.util.spec_from_file_location('acceptance',sys.argv[1]); "
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m); "
                "r=m.subprocess.run([sys.executable,'-X','utf8','-I','-B',*sys.argv[2:]],"
                "cwd=sys.argv[4],capture_output=True,text=True,encoding='utf-8',timeout=4); "
                "print(r.stdout,end='');print(r.stderr,end='',file=sys.stderr);sys.exit(r.returncode)")
        command = [PYTHON, "-X", "utf8", "-I", "-B", "-c", code, str(WRAPPER),
                   *command[5:]]
    if name in ("nested", "nested-restricted", "loss", "loss-suspended"):
        command = [sys.executable, "-B", "-m", MODULE, name, str(folder)]
    if name == "benchmark":
        setup_wall = time.perf_counter()
        setup_cpu = time.process_time()
        for i in range(14):
            subdir = folder / f"sample-{i}"
            subdir.mkdir()
            for j in range(1000):
                (subdir / str(j)).touch()
        signals["file_setup_CPU"] = time.process_time() - setup_cpu
        signals["file_setup_wall"] = time.perf_counter() - setup_wall

    def phase(label, details):
        if name == "nested-restricted" and label == "before-create":
            flags = m.D(1)
            m.checked(m.set_job(details["job"], 4, ctypes.byref(flags), ctypes.sizeof(flags)))
            signals["outer_job_ui_limit"] = flags.value
        if name == "close" and label == "close-handle" and not signals:
            signals["injection"] = label
            raise OSError("forced close failure before API call")
        if name == "write" and label == "receipt-write":
            signals["injection"] = label
            # Fail the real exclusive partial creation, leaving the existing marker intact.
            (folder / "guard/supervisor.json.partial").write_bytes(b"fixture write conflict")
        if name == "cleanup-race" and label == "before-terminate":
            signals["exited_during_cleanup"] = release_child(folder)
        if name == "enum-race" and label == "before-handle" and not signals:
            file = folder / "parent.child"
            if file.exists() and int(file.read_text()) == details["pid"]:
                signals["exited_before_acquisition"] = release_child(folder)
        if name == "breakaway" and label == "periodic" and not signals:
            marker = folder / "breakaway.child"
            if marker.exists() and marker.stat().st_size:
                handle = m.process_handle(int(marker.read_text()))
                try:
                    belongs = m.w.BOOL()
                    m.checked(m.is_in_job(handle, details["job"], ctypes.byref(belongs)))
                    signals["breakaway_still_in_job"] = bool(belongs.value)
                    (folder / "release").touch()
                finally:
                    m.checked(m.close(handle))

    start = time.perf_counter()
    parent_cpu = time.process_time()
    record = None
    outsider = None
    try:
        if name == "foreign":
            outsider = subprocess.Popen([PYTHON, "-I", "-B", "-c", "import time;time.sleep(3)"])
            fault = "process_handle"
            open_original = m.process_handle
            substitute = lambda pid: open_original(outsider.pid)
        options = dict(cwd=ROOT if name in ("nested", "nested-restricted", "loss", "loss-suspended") else folder,
                       env=env, expected_sha=pin, phase_hook=phase)
        if fault:
            with patch.object(m, fault, substitute):
                record = m.monitor(command, folder / "guard", folder, params, **options)
        else:
            record = m.monitor(command, folder / "guard", folder, params, **options)
        if outsider:
            signals["foreign_alive"] = outsider.poll() is None
    except Exception as exc:
        errors.append(dict(type=type(exc).__name__, message=str(exc)))
    finally:
        if outsider:
            if outsider.poll() is None:
                outsider.terminate()
            outsider.wait(timeout=4)
    wall = time.perf_counter() - start
    supervisor_cpu = time.process_time() - parent_cpu
    try:
        require_completion(folder / "guard", pin)
        admitted = True
    except (OSError, ValueError, KeyError, TypeError):
        admitted = False
    outcome = record["limit_reason"] if record else "write-error"
    ok = outcome == reason and admitted == (reason is None)
    if name == "final-only":
        ok &= bool(record and record["worker_CPU_seconds"] is None and
                   record["exit_code"] == 0 and signals.get("pre_fault_job", {}).get("active") == 0)
    if name in ("close", "write"):
        ok &= bool(signals.get("injection"))
    if name == "cleanup":
        ok &= any(e.get("phase") == "cleanup-unresolved" for e in record["error"])
    if name in ("enum-race", "cleanup-race"):
        ok &= bool(next(iter(signals.values()), None))
    if name == "foreign":
        ok &= bool(signals.get("foreign_alive")) and any("belongs" in e["message"] for e in record["error"])
    if name == "breakaway":
        log = (folder / "guard/stdout.log").read_text()
        ok &= signals.get("breakaway_still_in_job") is True or '"breakaway_winerror": 5' in log
    if name in ("normal", "wrapper-child"):
        lines = (folder / "guard/stdout.log").read_text(encoding="utf8").splitlines()
        if lines:
            decoded = next((json.loads(line) for line in lines if line.startswith('{"args":')), {})
            ok &= decoded.get("args") == command[-3:] and Path(decoded.get("cwd", ".")) == folder
            ok &= decoded.get("stdin") == "" and "stderr Юникод" in lines
            environment = decoded.get("env", {})
            ok &= all(environment.get(k) == "1" for k in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS"))
            ok &= all(k in environment and environment[k] is None for k in ("PYTHONPATH","PYTHONHOME"))
    if name == "wrapper-help":
        ok &= b"--current040-manifest-sha256" in (folder / "guard/stdout.log").read_bytes()
    if name in ("loss", "loss-suspended"):
        ok &= record["exit_code"] == 23 and not (folder / "inner/supervisor.json").exists()
        ok &= (folder / "loss-members.json").exists()
        if name == "loss-suspended":
            ok &= not list(folder.glob("*.started"))
    outcome = dict(case=name, checked=bool(ok), expected=reason, observed=outcome,
                   external_errors=errors, signals=signals, supervisor_CPU=supervisor_cpu,
                   elapsed=wall, receipt=record is not None, consumed=admitted)
    m.save(folder / "result.json", outcome)
    print(name, bool(ok), outcome["observed"], flush=True)


def loss(folder, suspended=False):
    def fault(phase, details):
        if suspended and phase == "created-suspended":
            m.save(folder / "loss-members.json",
                   [dict(pid=details["pid"], birth=m.identity(details["root"])[0])])
            os._exit(23)
        if not suspended and phase == "periodic" and list(folder.glob("*.started")):
            # Outer Job supervises fault injection independently.
            m.save(folder / "loss-members.json", [dict(pid=p, birth=identity[0])
                for p in m.members(details["job"])
                for h in [m.process_handle(p)] for identity in [m.identity(h)] if m.close(h)])
            os._exit(23)
    m.monitor([PYTHON, "-I", "-B", str(FIXTURE), "wait", str(folder)],
              folder / "inner", folder, DEFAULT_LIMITS, phase_hook=fault)


if __name__ == "__main__":
    action = sys.argv[1]
    if action in ("nested", "nested-restricted"):
        nested(Path(sys.argv[2]), action == "nested-restricted")
    elif action in ("loss", "loss-suspended"):
        loss(Path(sys.argv[2]), action == "loss-suspended")
    else:
        output = RAW / action
        output.mkdir(exist_ok=False)
        requested = sys.argv[2:]
        m.save(output / "selection.json", dict(cases=requested, source=sha(Path(m.__file__)),
               fixture=sha(FIXTURE), harness=sha(Path(__file__)), wrapper=sha(WRAPPER)))
        for name in requested:
            run_case(name, output / (name + " output Юникод"), sha(Path(m.__file__)))
