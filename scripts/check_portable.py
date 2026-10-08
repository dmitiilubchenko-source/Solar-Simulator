"""Extract a built ZIP to a new path and verify an isolated relocated runtime."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import zipfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    target=root/".tools"/f"portable relocated {datetime.now():%Y%m%d-%H%M%S}"
    target.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(args.archive) as archive:
        for member in archive.infolist():
            if not (target/member.filename).resolve().is_relative_to(target.resolve()):
                raise ValueError("Unsafe ZIP path")
        archive.extractall(target)
    folder=next(p for p in target.iterdir() if p.is_dir())
    runtime=folder/"runtime"
    probe="""
import json,pathlib,sys,tkinter,solar_native,numpy,matplotlib,scipy,solar_simulator
root=pathlib.Path(sys.executable).resolve().parent
assert pathlib.Path(sys.prefix).resolve()==root
for module in (solar_native,numpy,matplotlib,scipy,solar_simulator):
    assert pathlib.Path(module.__file__).resolve().is_relative_to(root)
window=tkinter.Tk(); window.withdraw()
library=pathlib.Path(window.tk.call('info','library')).resolve()
assert library.is_relative_to(root),(library,root)
window.destroy()
from solar_simulator.storage import load,save
from solar_simulator.experiment import advance,preset
from dataclasses import replace
experiment=advance(load('scenarios/spheres.json'),2000)
assert len(experiment.events)==2
save(experiment,'checkpoint-test.json')
a=preset('sun-earth'); a=replace(a,settings=replace(a.settings,integrator='dop853'))
assert advance(a,20).time>0
system=advance(load('scenarios/solar-system.json'),20)
assert len(system.bodies)==9 and system.origin is not None
pn=advance(load('scenarios/solar-system-1pn.json'),20)
assert len(pn.bodies)==9 and pn.settings.physics=='eih-1pn'
from solar_simulator.cli import report
assert report(pn)['physics']=='eih-1pn'
save(pn,'checkpoint-pn-test.json')
assert load('checkpoint-pn-test.json').settings.physics=='eih-1pn'
moon=advance(load('scenarios/solar-system-moon-1pn.json'),24)
assert len(moon.bodies)==10 and moon.settings.physics=='eih-1pn' and moon.origin is not None
assert moon.bodies[3].name=='Earth' and moon.bodies[4].name=='Moon'
save(moon,'checkpoint-moon-test.json')
assert len(load('checkpoint-moon-test.json').bodies)==10
j2=advance(load('scenarios/solar-system-moon-1pn-j2.json'),24)
assert len(j2.settings.figures)==1 and j2.settings.figures[0].body=='Earth'
assert report(j2)['orbital_angular_momentum_conserved'] is False
save(j2,'checkpoint-j2-test.json')
assert load('checkpoint-j2-test.json').settings.figures==j2.settings.figures
from solar_simulator.oblateness import earth_j2
initial=preset('solar-system-moon')
assert earth_j2(initial.bodies,initial.origin)==j2.settings.figures
q2=advance(load('scenarios/solar-system-moon-1pn-q2.json'),24)
assert len(q2.settings.figures)==2 and q2.orientation_work!=0
save(q2,'checkpoint-q2-test.json')
restored=load('checkpoint-q2-test.json')
assert restored.orientation_work==q2.orientation_work and restored.settings.figures==q2.settings.figures
assert advance(restored,24).time==172800
from importlib.resources import files
assert 'NumFOCUS' in files('solar_simulator.data').joinpath('ERFA-LICENSE.txt').read_text()
print(json.dumps(dict(prefix=str(root),tcl=str(library),events=len(experiment.events),isolated=sys.flags.isolated)))
"""
    environment=os.environ.copy()
    windows=Path(os.environ["SystemRoot"])
    environment["PATH"]=str(windows/"System32")+os.pathsep+str(windows)
    for name in ("PYTHONHOME","PYTHONPATH","TCL_LIBRARY","TK_LIBRARY"):
        environment.pop(name,None)
    output=subprocess.check_output([str(runtime/"python.exe"),"-B","-I","-c",probe],cwd=folder,text=True,env=environment)
    result=json.loads(output)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print(f"RELOCATED_DIR={folder}")


if __name__=="__main__":
    main()
