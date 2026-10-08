"""Windows distribution using this interpreter and tested installed dependencies.

No registry, PATH or global Python changes. Each build gets a new directory.
The runtime is licensed CPython; dependency metadata/licenses are retained.
"""
from collections import deque
from datetime import datetime
import hashlib
from importlib import metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from packaging.requirements import Requirement

ROOT=Path(__file__).resolve().parents[1]


def dependency_closure():
    queue=deque(["matplotlib","numpy","scipy"])
    found={}
    while queue:
        name=queue.popleft().lower().replace("_","-")
        if name in found:
            continue
        distribution=metadata.distribution(name)
        found[name]=distribution
        for value in distribution.requires or []:
            requirement=Requirement(value)
            if requirement.marker is None or requirement.marker.evaluate({"extra":""}):
                queue.append(requirement.name)
    return found


def copy_distribution(distribution,target):
    source_root=Path(distribution.locate_file("")).resolve()
    for relative in distribution.files or []:
        source=Path(distribution.locate_file(relative)).resolve()
        if not source.is_relative_to(source_root) or not source.is_file():
            continue  # entry-point launchers outside site-packages are unnecessary.
        relative_path=source.relative_to(source_root)
        if "__pycache__" in relative_path.parts or source.suffix==".pyc":
            continue
        destination=target/relative_path
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)


def unpack_wheel(path,target):
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            destination=(target/member.filename).resolve()
            if not destination.is_relative_to(target.resolve()):
                raise ValueError("Unsafe wheel path")
        archive.extractall(target)


def build():
    if sys.platform!="win32" or sys.prefix==sys.base_prefix:
        raise RuntimeError("Build from the project Windows .venv")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    project_version=__import__("tomllib").loads((ROOT/"pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    output=ROOT/"dist"/f"SolarSimulator-{project_version}-{stamp}"
    output.mkdir(parents=True,exist_ok=False)
    runtime=output/"runtime"
    runtime.mkdir()
    base=Path(sys.base_prefix)
    executable=Path(sys._base_executable)
    shutil.copy2(executable,runtime/"python.exe")
    windowed=executable.with_name(executable.name.replace("python","pythonw",1))
    shutil.copy2(windowed,runtime/"pythonw.exe")
    for path in base.glob("*.dll"):
        if "_d" not in path.stem:
            shutil.copy2(path,runtime/path.name)
    shutil.copy2(base/"LICENSE.txt",runtime/"LICENSE.txt")
    ignore=shutil.ignore_patterns("__pycache__","*.pyc","*.pdb","site-packages","test","tests","idlelib","turtledemo")
    for name in ("Lib","DLLs","tcl"):
        shutil.copytree(base/name,runtime/name,ignore=ignore)
    packages=runtime/"Lib"/"site-packages"
    packages.mkdir(exist_ok=True)
    dependencies=dependency_closure()
    for distribution in dependencies.values():
        copy_distribution(distribution,packages)
    wheels=ROOT/".tools"/"distribution-wheels"
    wheels.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,"-B","-m","pip","wheel","--no-deps","--wheel-dir",str(wheels),str(ROOT)],check=True)
    unpack_wheel(wheels/f"solar_simulator-{project_version}-py3-none-any.whl",packages)
    subprocess.run([sys.executable,"-B",str(ROOT/"scripts/build_native.py"),"--wheel"],check=True,cwd=ROOT)
    native_wheels=list((ROOT/".tools/wheels").glob("solar_native-*.whl"))
    native_wheel=max(native_wheels,key=lambda p:p.stat().st_mtime)
    unpack_wheel(native_wheel,packages)
    # _pth isolates imports from user packages, environment variables and registry.
    dll_name=f"python{sys.version_info.major}{sys.version_info.minor}"+("t" if __import__("sysconfig").get_config_var("Py_GIL_DISABLED") else "")
    (runtime/f"{dll_name}._pth").write_text(".\nLib\nDLLs\nLib/site-packages\nimport site\n",encoding="utf-8")
    (output/"Solar Simulator.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\n"runtime\\python.exe" -B -m solar_simulator gui\r\nif errorlevel 1 pause\r\n',encoding="ascii")
    (output/"USER-GUIDE.md").write_text(
        (ROOT/"docs/user-guide.md").read_text(encoding="utf-8").replace("(accuracy-validation.md)", "(docs/accuracy-validation.md)").replace("(ephemerides.md)", "(docs/ephemerides.md)").replace("(relativity.md)", "(docs/relativity.md)").replace("(moon.md)", "(docs/moon.md)").replace("(oblateness.md)", "(docs/oblateness.md)").replace("(orientation.md)", "(docs/orientation.md)"),
        encoding="utf-8")
    (output/"PHYSICS.md").write_text(
        (ROOT/"docs/physics.md").read_text(encoding="utf-8").replace("(accuracy-validation.md)","(docs/accuracy-validation.md)").replace("(relativity.md)","(docs/relativity.md)").replace("(oblateness.md)","(docs/oblateness.md)").replace("(orientation.md)","(docs/orientation.md)").replace("(user-guide.md)","(docs/user-guide.md)"),
        encoding="utf-8")
    documents=output/"docs"
    documents.mkdir()
    for name in ("physics.md","rust.md","user-guide.md","core-validation.md","core-validation.json","accuracy-validation.md","accuracy-validation.json","ephemerides.md","solar-system-reference.json","solar-system-validation.json","relativity.md","relativity-validation.json","moon.md","solar-system-moon-reference.json","moon-validation.json","oblateness.md","oblateness-validation.json","orientation.md","orientation-validation.json","orientation-spice-reference.json"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    orientation_doc=documents/"orientation.md"
    orientation_doc.write_text(orientation_doc.read_text(encoding="utf-8").replace(
        "../src/solar_simulator/data/ERFA-LICENSE.txt",
        "../runtime/Lib/site-packages/solar_simulator/data/ERFA-LICENSE.txt"),encoding="utf-8")
    from solar_simulator.experiment import preset, PRESETS
    from solar_simulator.storage import save
    scenarios=output/"scenarios"
    scenarios.mkdir()
    for name in PRESETS:
        save(preset(name,backend="python" if name.startswith("solar-system") else "rust"),scenarios/f"{name}.json")
    from dataclasses import replace
    system=preset("solar-system")
    save(replace(system,settings=replace(system.settings,physics="eih-1pn")),scenarios/"solar-system-1pn.json")
    system=preset("solar-system-moon")
    save(replace(system,settings=replace(system.settings,physics="eih-1pn")),scenarios/"solar-system-moon-1pn.json")
    from solar_simulator.oblateness import earth_j2, earth_moon_quadrupoles
    save(replace(system,settings=replace(system.settings,physics="eih-1pn",figures=earth_j2(system.bodies,system.origin))),
         scenarios/"solar-system-moon-1pn-j2.json")
    save(replace(system,settings=replace(system.settings,physics="eih-1pn",figures=earth_moon_quadrupoles(system.bodies,system.origin))),
         scenarios/"solar-system-moon-1pn-q2.json")
    manifest=dict(python=sys.version,python_abi=dll_name,project_version=project_version,
                  native_wheel=native_wheel.name,dependencies={name:d.version for name,d in dependencies.items()})
    (output/"BUILD-INFO.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    # Prove the copied runtime imports local packages and initializes real Tk.
    probe="import sys,pathlib,tkinter,solar_simulator,solar_native,numpy,matplotlib,scipy; from solar_simulator.experiment import advance,preset; r=tkinter.Tk(); r.withdraw(); r.destroy(); s=advance(preset('spheres',backend='rust'),2000); assert len(s.events)==2; from dataclasses import replace; a=preset('sun-earth'); a=replace(a,settings=replace(a.settings,integrator='dop853')); assert advance(a,20).time>0; assert len(advance(preset('solar-system'),20).bodies)==9; print(sys.prefix); print(pathlib.Path(solar_simulator.__file__).resolve()); print('portable Tk + native physics OK')"
    subprocess.run([str(runtime/"python.exe"),"-B","-I","-c",probe],check=True,cwd=output)
    smoke="import tkinter; from solar_simulator.app import Laboratory; from solar_simulator.experiment import preset; r=tkinter.Tk(); r.withdraw(); a=Laboratory(r,preset('spheres',backend='rust')); a._start(); r.after(1000,a.close); r.mainloop(); print('portable application OK')"
    subprocess.run([str(runtime/"python.exe"),"-B","-I","-c",smoke],check=True,cwd=output)
    archive=output.with_name(output.name+".zip")
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as file:
        for path in output.rglob("*"):
            if path.is_file():
                file.write(path,path.relative_to(output.parent))
    with archive.open("rb") as file:
        checksum=hashlib.file_digest(file,"sha256").hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{checksum}  {archive.name}\n",encoding="ascii")
    print(f"PORTABLE_DIR={output}\nPORTABLE_ZIP={archive}\nSHA256={checksum}")
    return output


if __name__=="__main__":
    build()
