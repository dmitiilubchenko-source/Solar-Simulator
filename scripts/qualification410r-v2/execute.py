"""Run the frozen preflight and one, fail-closed portable attempt."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import stat
import subprocess
import sys
import time
import traceback
import zipfile

import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = Path("C:/Users/Admin/Documents/Codex/Solar 410R v2 20261119")
SOURCE = Path("C:/Users/Admin/Desktop/Solar-candidate-040-version-407v")
OLD = Path("C:/Users/Admin/Desktop/Solar-acceptance-410R")
SUP = Path("C:/Users/Admin/Desktop/Solar-tooling-4103")
EVIDENCE = Path("C:/Users/Admin/Desktop/Solar-tooling-410E")
PACKAGE = Path("C:/Users/Admin/Desktop/Solar-packaging-040-4095")
WRITER = ROOT/"scripts/qualification410e/writer.py"
ARCHIVE = Path("C:/Users/Admin/Documents/Codex/Solar4095-20261116/SolarSimulator-0.4.0-20261116-4095.zip")
TOOLS = ROOT/".tools"
PLAN_FILE = HERE/"execution-plan.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha(Path(path).read_bytes())


def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True,timeout=15).strip()


def plan():
    assert PLAN_FILE.read_bytes() == (RAW/PLAN_FILE.name).read_bytes()
    return json.loads(PLAN_FILE.read_bytes())


def save(path,data):
    partial = path.with_suffix(path.suffix+".partial")
    with partial.open("x",encoding="utf8") as f:
        json.dump(data,f,indent=2,ensure_ascii=False,allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.rename(partial,path)


def guard_api(p):
    for file,key in (("monitor.py","monitor_sha"),("consumer.py","consumer_sha")):
        assert digest(SUP/"scripts/qualification4103"/file) == p[key]
    sys.path.insert(0,str(SUP))
    from scripts.qualification4103 import monitor
    from scripts.qualification4103.consumer import require_completion
    return monitor,require_completion


def check_pins(p):
    for worktree,expected in ((SUP,p["supervisor_tip"]),(EVIDENCE,p["evidence_tip"]),
            (OLD,p["historical_tip"]),(SOURCE,p["pins"]["runtime_commit"]),
            (PACKAGE,"d04dc9aa5ca3d95659fc996ea560f042016ce67e")):
        assert git(worktree,"rev-parse","HEAD")==expected and not git(worktree,"status","--porcelain")
    assert git(SOURCE,"rev-parse","HEAD^{tree}")==p["pins"]["runtime_tree"]
    assert git(ROOT,"branch","--show-current")=="codex/qualification-410r-v2"
    for file,key in (("scripts/check_portable.py","wrapper_sha"),("scripts/qualification410e/writer.py","writer_sha"),
                     ("scripts/qualification410e/audit.py","auditor_sha")):
        expected = subprocess.check_output(["git","-C",str(ROOT),"show",p["implementation_commit"]+":"+file])
        assert sha(expected)==digest(ROOT/file)==p[key]
    assert digest(ROOT/"scripts/qualification410e/admission-amendment410r-v2.json")==p["amendment_sha"]
    assert digest(OLD/"scripts/qualification410r/execution-plan.json")==p["parent_plan_sha"]
    assert digest(OLD/"scripts/qualification410r/resource-ledger.json")==p["historical_ledger_sha"]
    assert digest(PACKAGE/"scripts/check_portable.py")=="e332fca075e4dd686c3011a0f644c19e2af2210025badffb8117f516d74687a7"
    assert not git(ROOT,"diff",p["evidence_tip"],"--","src","rust","scenarios","scripts/check_portable.py",
                   "scripts/qualification410e","scripts/recompute_current040_v1.py")
    assert not TOOLS.exists()


def isolated_env(stage):
    env = dict(os.environ)
    for key in ("TEMP","TMP","TMPDIR","LOCALAPPDATA","APPDATA","MPLCONFIGDIR","USERPROFILE",
                "HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME"):
        folder = stage/key.lower()
        folder.mkdir()
        env[key] = str(folder)
    env["HOMEDRIVE"],env["HOMEPATH"]=os.path.splitdrive(env["USERPROFILE"])
    for key in ("PYTHONHOME","PYTHONPATH","PYTHONHASHSEED","TCL_LIBRARY","TK_LIBRARY"):
        env.pop(key,None)
    return env


def nested():
    p = plan()
    monitor, require = guard_api(p)
    stage = Path(p["outputs"]["preflight"])
    probe = json.loads((stage/"probe-command.json").read_bytes())
    monitor.monitor(probe["command"],stage/"inner",stage,dict(cpu_seconds=12,wall_seconds=25,
        private_bytes=512*1024**2,disk_bytes=512*1024**2),
        cwd=probe["cwd"],expected_sha=p["monitor_sha"])
    require(stage/"inner",p["monitor_sha"])


def preflight():
    t,cpu=time.perf_counter(),time.process_time()
    p=plan()
    check_pins(p)
    monitor, require=guard_api(p)
    machine=dict(build=sys.getwindowsversion().build,logical_cpus=len(psutil.Process().cpu_affinity()),
         available_ram=psutil.virtual_memory().available,free_disk=shutil.disk_usage(ROOT).free,
         cpu_percent=psutil.cpu_percent(interval=.3))
    assert machine["build"]==26200 and machine["logical_cpus"]>=2
    assert machine["available_ram"]>=3*1024**3 and machine["free_disk"]>=4*1024**3
    occupied=[]
    for process in psutil.process_iter(["pid","cmdline"]):
        try:
            args = process.info["cmdline"] or []
            if process.pid!=os.getpid() and any(
                Path(x).name in {"check_portable.py","recompute_current040_v1.py","check_project.py"}
                or x.startswith("scripts.qualification") for x in args[1:]
            ):
                occupied.append(process.pid)
        except (psutil.NoSuchProcess,psutil.AccessDenied):
            pass
    assert not occupied,occupied
    stage = Path(p["outputs"]["preflight"])
    stage.mkdir(exist_ok=False)
    stage_resolved = stage.resolve()
    assert ARCHIVE.stat().st_size==114633711 and digest(ARCHIVE)==p["pins"]["portable_sha256"]
    contract = ARCHIVE.with_name("asset-contract.json")
    assert digest(contract)=="969f44ec9d596f0165e59d037d5dc16a593ab9f2151791cfc1dfdea8e881ca9e"
    assets=json.loads(contract.read_bytes())
    body = stage/assets["root"]
    # Extract only after validating each immutable member. Exact file hashes and ZIP's
    # CRC are checked by reading to EOF. This discovery does not execute any solver.
    with zipfile.ZipFile(ARCHIVE) as z:
        assert len(z.infolist())==len(assets["files"])==6005
        seen=set()
        for f in z.infolist():
            parts=PurePosixPath(f.filename).parts
            assert len(parts)>1 and parts[0]==assets["root"] and ".." not in parts
            assert "\\" not in f.filename and ":" not in f.filename and not stat.S_ISLNK(f.external_attr>>16)
            rel="/".join(parts[1:])
            assert rel not in seen
            seen.add(rel)
            raw=z.read(f)
            expected=assets["files"][rel]
            assert len(raw)==expected["size"] and sha(raw)==expected["sha256"]
            destination=stage.joinpath(*parts).resolve()
            assert destination.is_relative_to(stage_resolved)
            destination.parent.mkdir(parents=True,exist_ok=True)
            with destination.open("xb") as handle:handle.write(raw)
        assert seen==set(assets["files"])
    manifest=body/"verification-current040/manifest-v1.json"
    manifest_pin=p["pins"]["current_manifest_sha256"]
    assert digest(manifest)==manifest_pin
    current=json.loads(manifest.read_bytes())
    wheel=Path("C:/Users/Admin/Documents/Codex/Solar407V-20261111/wheels/solar_native-0.4.0-cp314-cp314t-win_amd64.whl")
    assert digest(wheel)==current["wheel_SHA256"]=="5c2db314218484f5cb8b436de4479d5ecb069b56a5bd621eaa6e5cd5c70a5adb"
    assert (current["source_commit"],current["source_tree"],current["native_SHA256"])==(
        p["pins"]["runtime_commit"],p["pins"]["runtime_tree"],p["pins"]["native_sha256"])
    expected_inputs={p["pins"][key]["path"]:p["pins"][key]["sha256"] for key in ("reference","scenario","catalog_scenario")}
    assert all(digest(body/name)==value for name,value in expected_inputs.items())
    assert digest(body/"runtime/python.exe")==current["interpreter_SHA256"]
    assert sha((subprocess.check_output([p["command"][0],"-I","-B","-c",
        "import json; from solar_simulator.recipe import runtime_fingerprint; print(json.dumps(runtime_fingerprint('rust'),indent=2))"],
        cwd=SOURCE,env={**os.environ,"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1"},
        timeout=15).decode().replace("\r\n","\n")).encode())==current["qualified_source_environment_fingerprint"]

    target=stage/"evidence Юникод"
    target.mkdir()
    scoped=stage/"isolated environment"
    scoped.mkdir()
    env=isolated_env(scoped)
    args=dict(native_sha256=p["pins"]["native_sha256"],input_hashes=expected_inputs,wrapper=str(ROOT/"scripts/check_portable.py"))
    command=[str(body/"runtime/python.exe"),"-I","-B","-X","utf8",str(HERE/"packaged_probe.py"),
             json.dumps(args),str(WRITER),str(target),'Эпоха "тест"']
    save(stage/"probe-command.json",dict(command=command,cwd=str(body)))
    monitor.monitor([sys.executable,"-B",str(__file__),"nested"],stage/"outer",stage,
                    dict(cpu_seconds=18,wall_seconds=35,private_bytes=768*1024**2,disk_bytes=512*1024**2),
                    cwd=ROOT,env=env,expected_sha=p["monitor_sha"])
    outer=require(stage/"outer",p["monitor_sha"])
    inner=require(stage/"inner",p["monitor_sha"])
    observed=json.loads((stage/"inner/stdout.log").read_bytes())
    assert observed["external_unicode_marker"] and observed["solver_runs"]==0
    assert observed["loaded_writer_sha"]==p["writer_sha"]
    assert not TOOLS.exists()
    prep_cpu=time.process_time()-cpu+outer["worker_CPU_seconds"]
    prep_wall=time.perf_counter()-t
    preflight_bytes=monitor.disk_size(stage)
    assert prep_cpu+7+p["forecast"]["total_cpu"]<p["early"]["cpu_seconds"]
    assert prep_wall+20+p["forecast"]["wall"]<p["early"]["wall_seconds"]
    assert preflight_bytes+1024**3<p["early"]["disk_bytes"]
    receipt=dict(status="PASS",machine=machine,checks=dict(archive_crc_members=6005,manifest_sha=manifest_pin,
        wheel_sha=current["wheel_SHA256"],source_fingerprint=current["qualified_source_environment_fingerprint"],
        nested_job_pass=inner["complete"],packaged_probe=observed),
        measured_cpu=prep_cpu,measured_wall=prep_wall,preflight_data_bytes=preflight_bytes,
        estimated_peak_private=outer["peak_private_tree_sampled"],plan_sha=digest(PLAN_FILE),
        attempts_consumed=0,tool_sha=digest(Path(__file__)),probe_sha=digest(HERE/"packaged_probe.py"))
    save(RAW/"preflight.json",receipt)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


def worker():
    t,cpu=time.perf_counter(),time.process_time()
    p=plan()
    pre=json.loads((RAW/"preflight.json").read_bytes())
    assert pre["status"]=="PASS" and pre["plan_sha"]==digest(PLAN_FILE)
    assert pre["tool_sha"]==digest(Path(__file__)) and pre["probe_sha"]==digest(HERE/"packaged_probe.py")
    check_pins(p)
    monitor,require=guard_api(p)
    assert digest(ARCHIVE)==p["pins"]["portable_sha256"]
    assert psutil.virtual_memory().available>=3*1024**3 and shutil.disk_usage(ROOT).free>=4*1024**3
    for name in ("launch-reservation.json","dispatch.json","worker-measurement.json","worker-exception.txt"):
        assert not (RAW/name).exists()
    TOOLS.mkdir(exist_ok=False)
    staging=TOOLS/"isolated temporary files"
    staging.mkdir()
    env=isolated_env(staging)
    args = p["command"]
    assert args[4]==str(ROOT/"scripts/check_portable.py") and Path(args[5])==ARCHIVE
    assert args[6:]==["--current040-manifest-sha256",p["pins"]["current_manifest_sha256"]]
    reserve_cpu=40
    reserve_wall=65
    precharged=pre["measured_cpu"]+7+time.process_time()-cpu
    active_start=t-pre["measured_wall"]-20
    limits=dict(p["early"])
    limits["wall_seconds"]-=reserve_wall
    limits["disk_bytes"]-=pre["preflight_data_bytes"]
    save(RAW/"launch-reservation.json",dict(command=args,cwd=str(ROOT),disk_root=str(TOOLS),limits=limits,
        temporary_root=str(staging),plan_sha=digest(PLAN_FILE),worker_single_launch_lock=True))
    def dispatch(name, details):
        if name=="periodic" and not (RAW/"dispatch.json").exists():
            save(RAW/"dispatch.json",dict(attempts_consumed=1,reason="Root resumed; single-shot reserved",
                 timestamp=time.time()))
    record=None
    try:
        record=monitor.monitor(args,TOOLS/"supervisor",TOOLS,limits,used_cpu=precharged+reserve_cpu,
            stage_start=active_start,cwd=ROOT,env=env,expected_sha=p["monitor_sha"],phase_hook=dispatch)
        require(TOOLS/"supervisor",p["monitor_sha"])
    except BaseException:
        (RAW/"worker-exception.txt").write_text(traceback.format_exc(),encoding="utf8")
        raise
    finally:
        output=sorted(x.name for x in TOOLS.glob("portable relocated *"))
        attempted=(RAW/"dispatch.json").exists() or bool(output)
        save(RAW/"worker-measurement.json",dict(attempts_consumed=int(attempted),relocation_dirs=output,
             parent_cpu_including_receipt=time.process_time()-cpu,elapsed_wall=time.perf_counter()-t,
             worker_job_cpu=None if record is None else record["worker_CPU_seconds"],
             resource_guard_receipt=str(TOOLS/"supervisor/supervisor.json")))
    print("Validated persisted supervisor completion.")


if __name__=="__main__":
    try:
        {"preflight":preflight,"nested":nested,"worker":worker}[sys.argv[1]]()
    except BaseException:
        if sys.argv[1]=="preflight":
            (RAW/"preflight-failure.txt").write_text(traceback.format_exc(),encoding="utf8")
        raise
