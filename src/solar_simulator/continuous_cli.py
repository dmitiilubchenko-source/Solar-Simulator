"""Explicit experimental interval calculation; legacy GUI/defaults are unchanged."""
import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from importlib.util import find_spec
import json
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from .cli import report
from .continuous import ContinuousRun
from .state_export import export_state
from .storage import load, save


def _json(path, value):
    with path.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write("\n")


def run(input_path, target, output, *, packet_steps=20):
    """Write a new local run folder; never reuse or overwrite an existing one."""
    output=Path(output).resolve()
    if output.exists():raise FileExistsError("Папка результата уже существует: "+str(output))
    input_path=Path(input_path).resolve()
    raw=input_path.read_bytes()
    seed=load(input_path)
    session=ContinuousRun(seed,target)
    from .time_control import validate_target
    validate_target(seed,target,packet_steps)
    output.mkdir(parents=True,exist_ok=False)
    save(seed,output/"initial.json")
    metadata=dict(engine="bounded-continuous-dop853",experimental=True,
        input_sha256=hashlib.sha256(raw).hexdigest(),start_time_seconds=seed.time,
        target_time_seconds=float(target),packet_steps=packet_steps,settings=asdict(seed.settings),
        origin=asdict(seed.origin) if seed.origin else None,units="SI",
        scipy_version=__import__("scipy").__version__,
        source_sha256={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("continuous.py","continuous_cli.py","accuracy.py","native_forces.py",
                         "coordinates.py","error_control.py","oblateness.py","orientation.py")},
        controller_buffers_saved=False,validation_report="docs/continuous-integration-validation.md",
        automatically_scientifically_qualified=False,
        limitations=["Kepler e=.95 two-period 0.1m gate failed; this is an experimental numerical mode",
            "Published tests apply to their pinned profiles/horizons, not arbitrary input/settings",
            "Loading final.json starts a new controller; ordinary GUI continues using its original method",
            "Local error tolerances and energy conservation are not true physical precision"])
    import solar_native
    binary=Path(find_spec(solar_native.point_acceleration.__module__).origin)
    installed=[Path(find_spec("scipy.integrate._ivp."+name).origin) for name in ("base","rk")]
    dependencies={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [binary,*installed]}
    metadata["native_binary_sha256"]=dependencies[str(binary)]
    metadata["installed_scipy_source_sha256"]={path.name:dependencies[str(path)] for path in installed}
    rows=0;epochs=[]
    start=perf_counter()
    current=seed
    try:
        with (output/"snapshots.csv").open("x",encoding="utf-8",newline="") as stream:
            writer=csv.writer(stream)
            writer.writerow(("time_seconds","epoch_jd_tdb","name","mass_kg",
                             "x_m","y_m","z_m","vx_m_s","vy_m_s","vz_m_s","orientation_work_joules"))
            while True:
                epochs.append(current.time)
                for body in current.bodies:
                    writer.writerow((current.time,seed.origin.epoch_jd_tdb+current.time/86400 if seed.origin else "",
                        body.name,body.mass,body.position.x,body.position.y,body.position.z,
                        body.velocity.x,body.velocity.y,body.velocity.z,current.orientation_work))
                    rows+=1
                stream.flush()
                if session.finished:break
                current=session.next(packet_steps)
        if input_path.read_bytes()!=raw:raise ValueError("Input changed during run")
        if (any(hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()!=sha
                for name,sha in metadata["source_sha256"].items())
                or any(hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha for name,sha in dependencies.items())):
            raise ValueError("Scientific sources changed during run")
        save(current,output/"final.json")
        export_state(current,output/"final.csv")
        result=dict(metadata,status="complete",**session.statistics,elapsed_seconds=perf_counter()-start,
            sample_times_seconds=epochs,csv_rows=rows,final_report=report(current),solver_executed=bool(session.statistics["packets"]))
        result["output_sha256"]={name:hashlib.sha256((output/name).read_bytes()).hexdigest()
            for name in ("initial.json","snapshots.csv","final.json","final.csv")}
        _json(output/"receipt.json",result)
        return result
    except BaseException as error:
        committed=session.current
        save(committed,output/"interrupted.json")
        _json(output/"failure.json",dict(metadata,status="interrupted" if isinstance(error,KeyboardInterrupt) else "failed",
            last_committed_time_seconds=committed.time,error_type=type(error).__name__,error=str(error),
            **session.statistics))
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--target",type=float,required=True,help="Конечное время от начала опыта, SI секунды")
    parser.add_argument("--packet-steps",type=int,default=20)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args(argv)
    output=args.output
    if output is None:
        base=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))/"SolarSimulator"/"experiments"
        output=base/("continuous-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")+"-"+uuid4().hex[:8])
    print("Экспериментальный расчёт DOP853; применимость и ограничения сохраняются в receipt.json.",flush=True)
    result=run(args.input,args.target,output,packet_steps=args.packet_steps)
    print(json.dumps(dict(output_directory=str(output.resolve()),status=result["status"],
        final_time_seconds=result["final_report"]["time_seconds"],packets=result["packets"],
        rhs_calls=result["rhs_calls"],elapsed_seconds=result["elapsed_seconds"],experimental=True),
        ensure_ascii=False,allow_nan=False),flush=True)
    return 0


if __name__=="__main__":raise SystemExit(main())
