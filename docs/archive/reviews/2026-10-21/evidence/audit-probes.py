"""Repeat engineering probes; original evidence belongs to commit7066fce."""
import argparse
import ast
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter
from unittest.mock import patch


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[4])
    parser.add_argument('--output',type=Path,required=True,help='NEW output directory; old evidence is never overwritten')
    parser.add_argument('--benchmarks',action='store_true',help='Also measure 100/400/1000 packet recording')
    args=parser.parse_args(argv)
    ROOT=args.project.resolve();OUT=args.output.resolve()
    if not (ROOT/'src/solar_simulator/app.py').is_file():parser.error('Project source root not found')
    OUT.mkdir(parents=True,exist_ok=False)
    os.environ['LOCALAPPDATA']=str(OUT/'appdata')
    sys.path.insert(0,str(ROOT/'src'))
    from solar_simulator.experiment import Settings, create_experiment, advance
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    from solar_simulator.branch_io import save_experiment

    def seed():
        return create_experiment([Body('probe', 1., Vector3(0.,0.,0.), Vector3(1.,0.,0.))], Settings(1.))

    result = {'scope': 'Independent audit probes; no source modifications; no scientific accuracy certification'}
    counts = {}
    for directory in ('src', 'scripts', 'tests', 'rust'):
        paths = [p for p in (ROOT/directory).rglob('*') if p.suffix in ('.py', '.rs') and p.is_file()]
        counts[directory] = {'files': len(paths), 'lines': sum(len(p.read_text(encoding='utf-8-sig').splitlines()) for p in paths)}
    result['source_counts'] = counts
    result['syntax_errors'] = []
    for path in (ROOT/'src').rglob('*.py'):
        try:
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        except SyntaxError as error:
            result['syntax_errors'].append(str(error))

    import tkinter as tk
    from solar_simulator.app import Laboratory
    import solar_simulator.app as app_module
    from solar_simulator import recovery
    incoming = OUT/'incoming.json'
    save_experiment(seed(), incoming)
    progressed = advance(seed(), 10)
    root = tk.Tk()
    root.withdraw()
    app = Laboratory(root, progressed)
    replacement_results = []
    try:
        for name in ('_reset', '_new', '_load'):
            app._set_experiment(progressed)
            with patch.object(app_module, 'save_experiment') as saved, patch.object(recovery, 'save_recovery') as recovered, patch.object(app_module.filedialog, 'askopenfilename', return_value=str(incoming)):
                getattr(app, name)()
                replacement_results.append({'action': name, 'time_before': progressed.time,
                    'time_after': app.experiment.time, 'checkpoint_writes': saved.call_count,
                    'recovery_writes': recovered.call_count, 'old_state_still_current': app.experiment is progressed})
    finally:
        app.close()
    result['replace_unsaved_state'] = replacement_results
    print(json.dumps(result,ensure_ascii=False),flush=True)

    from solar_simulator import recipe
    from solar_simulator.trajectory import record_trajectory, Trajectory
    benchmarks = []
    if args.benchmarks:
        for packets in (100, 400, 1000):
            with tempfile.TemporaryDirectory(prefix=f'solar-bench-{packets}-',dir=OUT) as temp:
                directory = Path(temp)/'track'
                with patch.object(recipe,'runtime_fingerprint',return_value={'audit_fixture':True}):
                    before = perf_counter()
                    record_trajectory(seed(),directory,float(packets),packet_steps=1)
                    write_seconds = perf_counter()-before
                before = perf_counter()
                track = Trajectory(directory)
                read_seconds = perf_counter()-before
                benchmarks.append({'packets':packets,'frames':len(track.times),'write_seconds':write_seconds,
                    'read_seconds':read_seconds,'retained_frame_bytes':sum(map(len,track._raw_frames)),
                    'total_disk_bytes':sum(p.stat().st_size for p in directory.iterdir())})
                print(json.dumps(benchmarks[-1]),flush=True)
    result['trajectory_benchmark'] = {'fixture':'One ballistic body, Verlet dt=1, batch=1; dependency fingerprint stubbed to isolate recording cost; real atomic writer and full reader', 'measurements':benchmarks}
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
