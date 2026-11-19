"""Read-only audit of the single portable attempt, including a partial failure."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback
import zipfile

import numpy as np

from execute import ARCHIVE, HERE, RAW, ROOT, SUP, TOOLS, digest, plan, save

NAMES = ["Sun","Mercury","Venus","Earth","Moon","Mars","Jupiter","Saturn","Uranus","Neptune"]


def read(path):
    return json.loads(path.read_bytes())


def maxima(actual, expected):
    delta = actual-expected
    magnitude = lambda cols: max(math.hypot(*row) for row in delta[:,cols])
    return dict(position_metres=magnitude(slice(0,3)),velocity_m_per_s=magnitude(slice(3,6)))


def per_body(actual, reference, stored):
    rows = {name:dict(jpl_residual=maxima(actual[:,i],reference[:,i]),
                      stored_difference=maxima(actual[:,i],stored[:,i]))
            for i,name in enumerate(NAMES)}
    moon = maxima(actual[:,4]-actual[:,3],reference[:,4]-reference[:,3])
    old_moon = maxima(actual[:,4]-actual[:,3],stored[:,4]-stored[:,3])
    physical = max(x["jpl_residual"]["position_metres"] for x in rows.values())<10000 and moon["position_metres"]<1000
    reproduced = all(x["position_metres"]<.1 and x["velocity_m_per_s"]<1e-5
                     for x in (old_moon,*(r["stored_difference"] for r in rows.values())))
    return dict(results=rows,moon_relative_jpl=moon,moon_relative_stored_difference=old_moon,
                physical_goals_passed=physical,stored_reproduction_passed=reproduced)


def load_doc(bundle, relative, expected_sha):
    path=bundle/relative
    assert digest(path)==expected_sha,relative
    return read(path)


def examine_fresh(bundle, directory, pins):
    output = read(directory/"result.json")
    partial = {"record":output,"files":sorted(x.name for x in directory.iterdir())}
    states = directory/"states.jsonl"
    if not states.is_file() or not (directory/"propagated.npz").exists():
        partial["raw_rows"]=sum(1 for line in states.open(encoding="utf8") if line.strip()) if states.is_file() else 0
        return partial
    m=load_doc(bundle,"verification-current040/manifest-v1.json",pins["current_manifest_sha256"])
    initial=load_doc(bundle,"verification/initial.json",m["initial_SHA256"])
    ref=load_doc(bundle,"verification/reference.json",m["reference_SHA256"])
    stored=load_doc(bundle,"verification/trajectories.json",m["historical_files"]["trajectories.json"])
    assert initial["settings"]==m["settings"] and initial["origin"]==ref["origin"]==m["origin"]
    assert initial["units"]==m["units"]==ref["units"]=="SI"
    assert m["origin"]["frame"]=="Ecliptic J2000" and m["origin"]["center"]=="Solar System Barycenter"
    assert [b["name"] for b in initial["bodies"]]==[b["name"] for b in ref["bodies"]]==NAMES
    assert m["epochs_jd_tdb"]==ref["epochs_jd_tdb"] and m["packet_steps"]==20
    times=(np.array(ref["epochs_jd_tdb"])-initial["origin"]["epoch_jd_tdb"])*86400
    with np.load(directory/"propagated.npz",allow_pickle=False) as z:
        actual=z["states"]
        assert np.array_equal(z["times"],times)
    records=[json.loads(line) for line in states.read_text(encoding="utf8").splitlines()]
    assert len(times)==len(records)==125 and times[0]==0 and times[-1]==31557600
    assert actual.shape==(125,10,6) and actual.dtype==np.float64 and np.isfinite(actual).all()
    assert np.array_equal(actual,np.array([row["states"] for row in records]))
    assert np.array_equal(times,np.array([row["time"] for row in records]))
    assert np.array_equal(actual[0],np.array([b["position"]+b["velocity"] for b in initial["bodies"]]))
    expected=np.array([[row["position"]+row["velocity"] for row in b["states"]] for b in ref["bodies"]]).transpose(1,0,2)
    recomputed=per_body(actual,expected,np.array(stored["profiles"]["rust_tighter"]))
    assert all(output[k]==v for k,v in recomputed.items())
    assert output["solver_executed"] is True and output["packets"]>0 and output["samples"]==125
    assert output["manifest_SHA256"]==pins["current_manifest_sha256"] and output["duration_seconds"]==31557600
    assert math.isfinite(output["energy_residual"])
    partial.update(recomputed=recomputed,raw_rows=len(records),raw_sha256={name:digest(directory/name)
                   for name in ("result.json","propagated.npz","states.jsonl")})
    return partial


def history_from_inputs(bundle, current, claimed):
    ref=load_doc(bundle,"verification/reference.json",current["historical_files"]["reference.json"])
    traj=load_doc(bundle,"verification/trajectories.json",current["historical_files"]["trajectories.json"])
    assert digest(bundle/"verification/manifest.json")==claimed["manifest_sha256"]
    assert claimed["solver_executed"] is False and claimed["samples"]==125 and claimed["bodies"]==10
    assert claimed["checks_passed"] is True and claimed["prior_numerical_failure_retained"] is True
    assert [b["name"] for b in ref["bodies"]]==NAMES and ref["epochs_jd_tdb"]==traj["epochs_jd_tdb"]
    reference=np.array([[row["position"]+row["velocity"] for row in b["states"]] for b in ref["bodies"]]).transpose(1,0,2)
    for profile, sequence in traj["profiles"].items():
        states=np.array(sequence)
        profile_claimed=claimed["results"][profile]
        reconstructed=per_body(states,reference,states)
        assert profile_claimed["jpl_residuals"]=={n:r["jpl_residual"] for n,r in reconstructed["results"].items()}
        assert profile_claimed["moon_relative_jpl"]==reconstructed["moon_relative_jpl"]
        assert profile_claimed["physical_goals_passed"]==reconstructed["physical_goals_passed"]


def liveness(record, p):
    assert digest(SUP/"scripts/qualification4103/monitor.py")==p["monitor_sha"]
    assert digest(SUP/"scripts/qualification4103/consumer.py")==p["consumer_sha"]
    sys.path.insert(0,str(SUP))
    from scripts.qualification4103 import monitor as m
    from scripts.qualification4103.consumer import require_completion
    checked=[]
    for proc in record["processes"]:
        try:
            handle=m.process_handle(proc["pid"])
        except OSError as exc:
            if getattr(exc,"winerror",None)!=87:
                raise
            gone=True
        else:
            try:gone=m.identity(handle)[0]!=proc["creation_FILETIME"] or m.wait(handle,0)==0
            finally:m.checked(m.close(handle))
        checked.append(dict(pid=proc["pid"],creation_FILETIME=proc["creation_FILETIME"],gone=gone))
    assert all(row["gone"] for row in checked)
    assert record["final_job"]["active"]==0
    consumer=None
    try:require_completion(TOOLS/"supervisor",p["monitor_sha"])
    except ValueError as exc:consumer=str(exc)
    return dict(checked=checked,consumer_accepted=consumer is None,consumer_rejection=consumer)


def run():
    wall,cpu=time.perf_counter(),time.process_time()
    p=plan()
    assert digest(ARCHIVE)==p["pins"]["portable_sha256"] and ARCHIVE.stat().st_size==114633711
    assert digest(ROOT/"scripts/check_portable.py")==p["wrapper_sha"]
    assert digest(ROOT/"scripts/qualification410e/writer.py")==p["writer_sha"]
    assert digest(ROOT/"scripts/qualification410e/audit.py")==p["auditor_sha"]
    reservation=read(RAW/"launch-reservation.json")
    assert reservation["command"]==p["command"] and reservation["cwd"]==p["cwd"]
    assert reservation["plan_sha"]==digest(HERE/"execution-plan.json")
    assert reservation["disk_root"]==str(TOOLS)
    assert read(RAW/"dispatch.json")["attempts_consumed"]==1
    measurement=read(RAW/"worker-measurement.json")
    assert measurement["attempts_consumed"]==1
    record=read(TOOLS/"supervisor/supervisor.json")
    assert record["monitor_SHA256"]==p["monitor_sha"] and record["worker_CPU_seconds"]==measurement["worker_job_cpu"]
    status=liveness(record,p)
    relocations=list(TOOLS.glob("portable relocated *"))
    assert len(relocations)==1
    parent=relocations[0]
    bundle=parent/"SolarSimulator-0.4.0-4095"
    log=TOOLS/"supervisor/stdout.log"
    outputs={"bundle":str(bundle),"log_sha256":digest(log),"files":sorted(x.name for x in parent.iterdir())}
    # Runtime files are immutable. Workflow artifacts may differ from their
    # original inputs under the extracted package root.
    current=load_doc(bundle,"verification-current040/manifest-v1.json",p["pins"]["current_manifest_sha256"])
    assert all(digest(bundle/"runtime"/rel)==expected for rel,expected in current["runtime_files"].items())
    assert all(digest(bundle/"verification"/rel)==expected for rel,expected in current["historical_files"].items())
    with zipfile.ZipFile(ARCHIVE) as z:
        assert len(z.infolist())==6005
        for key in ("reference","scenario","catalog_scenario"):
            rel=p["pins"][key]["path"]
            expected=p["pins"][key]["sha256"]
            assert digest(bundle/rel)==expected
            assert hashlib.sha256(z.read(bundle.name+"/"+rel)).hexdigest()==expected
    fresh=parent/(bundle.name+"-fresh-current040-raw")
    if (fresh/"result.json").exists():
        outputs["fresh_year"]=examine_fresh(bundle,fresh,p["pins"])
    if status["consumer_accepted"]:
        text=log.read_text(encoding="utf8").lstrip()
        stdout,end=json.JSONDecoder().raw_decode(text)
        assert text[end:].strip()==f"RELOCATED_DIR={bundle}"
        assert stdout["isolated"]==1 and Path(stdout["prefix"]).resolve()==bundle/"runtime"
        assert Path(stdout["tcl"]).resolve().is_relative_to(bundle/"runtime")
        assert stdout["gui"]["isolated"]==stdout["recovery"]["isolated"]==stdout["patch031_workflows"]["isolated"]==1
        for section, keys in (
            ("gui",("footer_visible","GUI_save_load_reset_continue","solar_target_pause_save_resume",
                    "GUI_add_body_saved_parent","GUI_parent_restore_saved_child","GUI_remove_sun_free_motion",
                    "isolated_CLI_CSV","strict_checkpoint_sha256","GUI_strict_load_and_exact_target")),
            ("recovery",("CLI_finished_result_recovered","CLI_local_fallback")),
            ("patch031_workflows",("reader_off_Tk_thread","Tk_heartbeat","cancellation_preserves_recording",
                                  "analytic_free_motion_frames","playback_no_solver","persistent_artists"))):
            assert all(stdout[section][k] is True for k in keys)
        assert set(stdout["recording_workflows"])=={"create","restore"}
        assert all(row["isolated"]==1 for row in stdout["recording_workflows"].values())
        claim=stdout["fresh_year"]
        assert outputs["fresh_year"]["record"]==claim
        assert all(outputs["fresh_year"]["recomputed"][k] for k in ("physical_goals_passed","stored_reproduction_passed"))
        history_from_inputs(bundle,current,stdout["jpl_replay"])
        spec=importlib.util.spec_from_file_location("fixed_auditor",ROOT/"scripts/qualification410e/audit.py")
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        outputs["continuous_recomputed"]=module.audit_portable(
            ARCHIVE,bundle,ROOT/"scripts/check_portable.py",p["wrapper_sha"],
            ROOT/"scripts/qualification410e/writer.py",p["writer_sha"],log)
        outputs["wrapper_stdout"]=stdout
    else:
        outputs["failure_log"]=log.read_text(encoding="utf8",errors="replace")[-16000:]
    summary=dict(complete=status["consumer_accepted"],liveness=status,outputs=outputs,
                 worker=dict(exit_code=record["exit_code"],limit_reason=record["limit_reason"],errors=record["error"],
                             attempts_consumed=1,worker_job_cpu=record["worker_CPU_seconds"],
                             peak_private=record["peak_private_tree_sampled"],disk_bytes=record["disk_bytes"]),
                 auditor_cpu=time.process_time()-cpu,auditor_wall=time.perf_counter()-wall)
    save(RAW/"independent-audit.json",summary)
    print(json.dumps(dict(complete=summary["complete"],worker=summary["worker"],
          outputs=list(outputs),auditor_cpu=summary["auditor_cpu"],auditor_wall=summary["auditor_wall"])))


if __name__=="__main__":
    try:run()
    except BaseException:
        (RAW/"independent-audit-error.txt").write_text(traceback.format_exc(),encoding="utf8")
        raise
