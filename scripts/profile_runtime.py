"""Separate physics/diagnostics/solver restarts and real Tk redraw costs."""
import argparse
import cProfile
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import statistics
from time import perf_counter
from unittest.mock import patch

from solar_simulator.application_profiles import solar_sandbox
from solar_simulator.cli import report
from solar_simulator.storage import to_document
from solar_simulator.time_control import advance_towards

ROOT=Path(__file__).resolve().parents[1]
PACKETS=60
DURATION=3600*20*PACKETS


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
        separators=(",",":"),allow_nan=False).encode('utf-8')).hexdigest()


def track(backend,diagnostics,*,capture=False,one_interval=False):
    state=solar_sandbox(backend=backend);frames=[];energies=[]
    start=perf_counter()
    if one_interval:
        state=advance_towards(state,float(DURATION),20*PACKETS)
    else:
        for _ in range(PACKETS):
            state=advance_towards(state,float(DURATION),20)
            values=report(state) if diagnostics else None
            if capture:
                frames.append({b.name:(b.position.x,b.position.y,b.position.z) for b in state.bodies})
                energies.append((state.time,values['energy_budget_residual_joules']))
    elapsed=perf_counter()-start
    return state,elapsed,frames,energies


def physics(output):
    rows={};captured=None
    for backend in ('python','rust'):
        cases={};snapshots=[]
        for diagnostics in (False,True):
            track(backend,diagnostics)
            times=[]
            for _ in range(3):
                state,elapsed,_,_=track(backend,diagnostics);times.append(elapsed)
                snapshots.append(digest(to_document(state)))
            cases['with_report' if diagnostics else 'physics_only']=dict(raw_seconds=times,median_seconds=statistics.median(times))
        assert len(set(snapshots))==1,'Diagnostics changed the experiment'
        state,_,_,_=track(backend,False,one_interval=True)
        single=[]
        for _ in range(3):
            state,elapsed,_,_=track(backend,False,one_interval=True);single.append(elapsed)
        multi,_,frames,energies=track(backend,True,capture=True)
        position=max(a.position.distance_to(b.position) for a,b in zip(state.bodies,multi.bodies))
        counts=[]
        from solar_simulator import accuracy
        original=accuracy.solve_ivp
        def observed(*args,**kwargs):
            result=original(*args,**kwargs)
            counts.append(dict(nfev=int(result.nfev),stored_times=len(result.t)))
            return result
        with patch('solar_simulator.accuracy.solve_ivp',observed):track(backend,False)
        profiler=cProfile.Profile();profiler.runcall(track,backend,True)
        profiler.dump_stats(str(output.parent/f'{backend}-runtime135.prof'))
        timer=[];values=report(multi)
        for _ in range(3):
            start=perf_counter()
            for _ in range(60):assert report(multi)==values
            timer.append((perf_counter()-start)/60)
        rows[backend]=dict(**cases,checkpoint_sha256=snapshots[0],single_interval_seconds=single,
            single_interval_median_seconds=statistics.median(single),partition_max_position_difference_metres=position,
            solve_ivp_calls=len(counts),rhs_calls=sum(r['nfev'] for r in counts),
            report_per_call_seconds=timer,report_median_seconds=statistics.median(timer),
            note='nfev counts RHS evaluations; accepted/rejected internal steps not recorded; profiler timings separate')
        if backend=='rust':captured=dict(checkpoint=to_document(multi),frames=frames,energies=energies)
    inputs=output.parent/'render-input135.json'
    inputs.write_text(json.dumps(captured,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    return dict(profile=asdict(solar_sandbox().settings),origin=asdict(solar_sandbox().origin),
        duration_seconds=DURATION,packets=PACKETS,results=rows,render_input_sha256=hashlib.sha256(inputs.read_bytes()).hexdigest())


def render(source,inputs,output):
    import tkinter as tk
    import tracemalloc
    from solar_simulator.storage import from_document
    spec=importlib.util.spec_from_file_location('solar_simulator._profile_app',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    data=json.loads(inputs.read_text(encoding='utf-8'));state=from_document(data['checkpoint'])
    root=tk.Tk();app=module.Laboratory(root,state);root.update();root.withdraw()
    results=[]
    try:
        app.canvas.draw_idle=lambda:None
        values=report(state);before=to_document(state)
        for history in (60,1500):
            frames=[data['frames'][i%60] for i in range(history)]
            energies=[data['energies'][i%60] for i in range(history)]
            for view in ('Все тела','Земля и Луна'):
                app.view.set(view);app.reference.set('Тело: Earth' if view=='Земля и Луна' else 'Инерциальная')
                app.frames.clear();app.frames.extend(frames)
                app.energies.clear();app.energies.extend(energies)
                app._draw(values);app.canvas.draw()
                build=[];paint=[]
                for _ in range(5):
                    start=perf_counter();app._draw(values);middle=perf_counter();app.canvas.draw();end=perf_counter()
                    build.append(middle-start);paint.append(end-middle)
                tracemalloc.start();app._draw(values);app.canvas.draw();_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                results.append(dict(history=history,view=view,build_raw_seconds=build,draw_raw_seconds=paint,
                    build_median_seconds=statistics.median(build),draw_median_seconds=statistics.median(paint),
                    full_raw_seconds=[a+b for a,b in zip(build,paint)],
                    full_median_seconds=statistics.median(a+b for a,b in zip(build,paint)),python_peak_bytes=peak,
                    limits=dict(x=list(app.orbit.get_xlim()),y=list(app.orbit.get_ylim())),
                    figure_pixels=list(app.canvas.get_width_height())))
                from PIL import Image
                import numpy as np
                suffix='relative' if view=='Земля и Луна' else 'all'
                Image.fromarray(np.asarray(app.canvas.buffer_rgba()).copy()).save(
                    output.with_name(output.stem+f'-{history}-{suffix}.png'))
        assert to_document(state)==before and to_document(app.experiment)==before
    finally:app.close()
    return dict(app_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                input_sha256=hashlib.sha256(inputs.read_bytes()).hexdigest(),results=results,
                notes='Synchronous hidden Tk canvas after real1180x820 layout; repeated data for1500 stress, not1500 integration packets. tracemalloc run excluded from timing; native allocations not fully measured. No polling latency/worker overlap.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('physics','render'));parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source',type=Path,default=ROOT/'src/solar_simulator/app.py')
    parser.add_argument('--inputs',type=Path,default=ROOT/'.tools/performance135/render-input135.json')
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Preserve previous profiling receipt')
    import scipy,numpy,matplotlib
    result=physics(args.output) if args.mode=='physics' else render(args.source,args.inputs,args.output)
    result.update(protocol='docs/runtime-performance-protocol.md',python=platform.python_version(),
        versions=dict(numpy=numpy.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__))
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':main()
