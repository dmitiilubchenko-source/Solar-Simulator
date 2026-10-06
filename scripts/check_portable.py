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
import json,pathlib,sys,tkinter,solar_native,numpy,matplotlib,solar_simulator
root=pathlib.Path(sys.executable).resolve().parent
assert pathlib.Path(sys.prefix).resolve()==root
for module in (solar_native,numpy,matplotlib,solar_simulator):
    assert pathlib.Path(module.__file__).resolve().is_relative_to(root)
window=tkinter.Tk(); window.withdraw()
library=pathlib.Path(window.tk.call('info','library')).resolve()
assert library.is_relative_to(root),(library,root)
window.destroy()
from solar_simulator.storage import load,save
from solar_simulator.experiment import advance
experiment=advance(load('scenarios/spheres.json'),2000)
assert len(experiment.events)==2
save(experiment,'checkpoint-test.json')
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
