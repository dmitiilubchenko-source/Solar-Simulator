"""Display-only comparison with a pinned previous viewer; no solver is run."""
from pathlib import Path
import argparse
import json,subprocess,types,time,statistics
from types import SimpleNamespace
import tkinter as tk
import numpy as np
from solar_simulator.trajectory_view import TrajectoryViewer
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Refusing to overwrite a previous measurement')
    ROOT=Path(__file__).resolve().parents[1]
    oldcode=subprocess.run(['git','show','dda0238:src/solar_simulator/trajectory_view.py'],cwd=ROOT,capture_output=True,check=True).stdout.decode()
    old=types.ModuleType('solar_simulator.old_view');old.__package__='solar_simulator';exec(compile(oldcode,'baseline-viewer','exec'),old.__dict__)
    root=tk.Tk();root.withdraw();results=[]
    for count in (10,354):
        names=[f'B{i}' for i in range(count)]
        states=[SimpleNamespace(bodies=[SimpleNamespace(name=name,position=SimpleNamespace(x=float(i+k),y=float(2*i-k),z=float(i+2*k))) for i,name in enumerate(names)]) for k in range(120)]
        track=SimpleNamespace(times=tuple(range(120)),metadata={'status':'complete'},directory=Path('synthetic-display-fixture'),frame=lambda i:(states[i],None))
        for label,cls in [('before',old.TrajectoryViewer),('after',TrajectoryViewer)]:
            viewer=cls(tk.Toplevel(root),track);viewer.window.withdraw()
            if viewer._timer is not None:viewer.window.after_cancel(viewer._timer);viewer._timer=None
            samples=[];coordinates=[]
            for repeat in range(6):
                begin=time.perf_counter()
                for index in (15,40,80,119):
                    viewer.player.seek(index);viewer._draw();viewer.canvas.draw()
                    segments=viewer.axis.collections[0].get_segments()
                    assert len(segments)==count
                    np.testing.assert_array_equal(segments[-1][-1],[float(count-1+index),float(2*(count-1)-index)])
                samples.append(time.perf_counter()-begin)
            results.append(dict(bodies=count,mode=label,frames=120,draws_per_sample=4,samples_seconds=samples,median_seconds=statistics.median(samples),collections=len(viewer.axis.collections)))
            viewer.close()
    root.destroy()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'scope':'display only; same deterministic coordinates, 120frames, synchronous canvas draw; six samples per variant; no solver or precision changes','results':results},indent=2)+'\n')
    print(json.dumps(results))


if __name__=='__main__':main()
