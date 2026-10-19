"""Windows distribution using this interpreter and tested installed dependencies.

No registry, PATH or global Python changes. Each build gets a new directory.
The runtime is licensed CPython; dependency metadata/licenses are retained.
"""
from collections import deque
from datetime import datetime
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from packaging.requirements import Requirement
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename
from packaging.version import Version

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_DOCUMENT_ARCHIVES={
    'docs/de441-reader-inputs.zip','docs/nominal-jpl440-inputs.zip',
    'docs/runtime-sources-before301.zip','tests/data/jpl-verification.zip',
}


def candidate_versions(root=ROOT):
    """Validate the product's paired Python/Rust versions before creating output."""
    import tomllib
    python=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    rust={crate:tomllib.loads((root/f'rust/{crate}/Cargo.toml').read_text(encoding='utf-8'))['package']['version']
          for crate in ('solar_core','solar_native')}
    native=tomllib.loads((root/'rust/solar_native/pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    if any(Version(value)!=Version(python) for value in (*rust.values(),native)):
        raise ValueError(f'Python/Rust release versions disagree: {python}, {rust}, native wheel {native}')
    return python,rust


def select_native_wheel(directory,version):
    """Reject stale or ambiguous artifacts instead of trusting modification time."""
    supported=set(sys_tags())
    candidates=[]
    for path in directory.glob('solar_native-*.whl'):
        name,actual,_,tags=parse_wheel_filename(path.name)
        if name=='solar-native' and actual==Version(version) and tags & supported:
            candidates.append(path)
    if len(candidates)!=1:
        raise ValueError(f'Expected one compatible solar-native {version} wheel; found {len(candidates)}')
    return candidates[0]


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


def run_build_smokes(executable,output,probes):
    """Keep generated recovery/font files out of both the user profile and ZIP."""
    tools=(ROOT/'.tools').resolve()
    tools.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='portable-smoke-',dir=tools) as temporary:
        scratch=Path(temporary).resolve()
        if scratch.parent!=tools:
            raise ValueError('Smoke cleanup must stay inside the build tools directory')
        environment=os.environ.copy()
        for name in ('PYTHONHOME','PYTHONPATH','TCL_LIBRARY','TK_LIBRARY'):
            environment.pop(name,None)
        environment['LOCALAPPDATA']=str(scratch/'user data')
        environment['MPLCONFIGDIR']=str(scratch/'matplotlib')
        if os.name=='nt':
            windows=Path(os.environ['SystemRoot'])
            environment['PATH']=str(windows/'System32')+os.pathsep+str(windows)
        for probe in probes:
            subprocess.run([str(executable),'-B','-I','-c',probe],check=True,cwd=output,
                           env=environment,timeout=120)


def build():
    if sys.platform!="win32" or sys.prefix==sys.base_prefix:
        raise RuntimeError("Build from the project Windows .venv")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    project_version,rust_versions=candidate_versions()
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
    native_wheel=select_native_wheel(ROOT/'.tools/wheels',rust_versions['solar_native'])
    unpack_wheel(native_wheel,packages)
    # _pth isolates imports from user packages, environment variables and registry.
    dll_name=f"python{sys.version_info.major}{sys.version_info.minor}"+("t" if __import__("sysconfig").get_config_var("Py_GIL_DISABLED") else "")
    (runtime/f"{dll_name}._pth").write_text(".\nLib\nDLLs\nLib/site-packages\nimport site\n",encoding="utf-8")
    (output/"Solar Simulator.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\n"runtime\\python.exe" -B -m solar_simulator gui\r\nif errorlevel 1 pause\r\n',encoding="ascii")
    rotation_documents=prepare_documents(output)
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
    from solar_simulator.oblateness import earth_j2, earth_moon_quadrupoles,solar_j2,sun_earth_moon_quadrupoles
    save(replace(system,settings=replace(system.settings,physics="eih-1pn",figures=earth_j2(system.bodies,system.origin))),
         scenarios/"solar-system-moon-1pn-j2.json")
    save(replace(system,settings=replace(system.settings,physics="eih-1pn",figures=earth_moon_quadrupoles(system.bodies,system.origin))),
         scenarios/"solar-system-moon-1pn-q2.json")
    save(replace(system,settings=replace(system.settings,physics="eih-1pn",figures=earth_moon_quadrupoles(system.bodies,system.origin),
                                       relative_pair=("Earth","Moon"),position_atol=1e-5,velocity_atol=1e-11)),
         scenarios/"solar-system-moon-1pn-q2-relative.json")
    save(replace(system,settings=replace(system.settings,physics="eih-1pn",figures=sun_earth_moon_quadrupoles(system.bodies,system.origin),
                                       relative_pair=("Earth","Moon"),position_atol=1e-5,velocity_atol=1e-11)),
         scenarios/"solar-system-moon-1pn-solar-q2-relative.json")
    system=preset("solar-system")
    save(replace(system,settings=replace(system.settings,physics="eih-1pn",figures=solar_j2(system.bodies,system.origin))),
         scenarios/"solar-system-1pn-solar-j2.json")
    system=preset("solar-system-pluto")
    save(replace(system,settings=replace(system.settings,physics="eih-1pn",figures=sun_earth_moon_quadrupoles(system.bodies,system.origin),
        relative_pair=("Earth","Moon"),rtol=3e-14,position_atol=1e-5,velocity_atol=1e-11)),
        scenarios/"solar-system-pluto-1pn-solar-q2-relative.json")
    system=preset("solar-system-asteroids")
    save(replace(system,settings=replace(system.settings,physics="eih-1pn",figures=sun_earth_moon_quadrupoles(system.bodies,system.origin),
        relative_pair=("Earth","Moon"),rtol=3e-14,position_atol=1e-5,velocity_atol=1e-11)),
        scenarios/"solar-system-asteroids-1pn-solar-q2-relative.json")
    system=preset("solar-system-asteroids-full")
    save(replace(system,settings=replace(system.settings,physics="eih-1pn",figures=sun_earth_moon_quadrupoles(system.bodies,system.origin),
        relative_pair=("Earth","Moon"),rtol=3e-14,position_atol=1e-5,velocity_atol=1e-11)),
        scenarios/"solar-system-asteroids-full-1pn-solar-q2-relative.json")
    save(replace(system,settings=replace(system.settings,backend="rust",physics="eih-1pn",
        figures=sun_earth_moon_quadrupoles(system.bodies,system.origin),relative_pair=("Earth","Moon"),
        rtol=3e-14,position_atol=1e-5,velocity_atol=1e-11)),
        scenarios/"solar-system-asteroids-full-rust-1pn-solar-q2-relative.json")
    system=preset("solar-system-asteroids-catalog",backend="rust")
    save(replace(system,settings=replace(system.settings,integrator="dop853",physics="eih-1pn",
        figures=sun_earth_moon_quadrupoles(system.bodies,system.origin),relative_pair=("Earth","Moon"),
        rtol=3e-14,position_atol=1e-7,velocity_atol=1e-13)),
        scenarios/"solar-system-asteroids-catalog-rust-1pn-solar-q2-relative.json")
    system=preset("solar-system-kuiper",backend="rust")
    save(replace(system,settings=replace(system.settings,integrator="dop853",physics="eih-1pn",
        figures=sun_earth_moon_quadrupoles(system.bodies,system.origin),relative_pair=("Earth","Moon"),
        rtol=3e-14,position_atol=1e-7,velocity_atol=1e-13)),
        scenarios/"solar-system-kuiper-rust-1pn-solar-q2-relative.json")
    system=preset("solar-system-kuiper-ring",backend="rust")
    save(replace(system,settings=replace(system.settings,integrator="dop853",physics="eih-1pn",
        figures=sun_earth_moon_quadrupoles(system.bodies,system.origin),relative_pair=("Earth","Moon"),
        rtol=3e-14,position_atol=1e-7,velocity_atol=1e-13)),
        scenarios/"solar-system-kuiper-ring-rust-1pn-solar-q2-relative.json")
    from solar_simulator.kuiper_ring import solar_system_ring
    from solar_simulator.experiment import create_experiment
    bodies,origin=solar_system_ring(144,0)
    refined=create_experiment(bodies,replace(system.settings,integrator="dop853",physics="eih-1pn",
        figures=sun_earth_moon_quadrupoles(bodies,origin),relative_pair=("Earth","Moon"),
        rtol=3e-14,position_atol=1e-7,velocity_atol=1e-13),origin=origin)
    save(refined,scenarios/"solar-system-kuiper-ring-144-rust-1pn-solar-q2-relative.json")
    from solar_simulator.application_profiles import lunar_rotation
    rotating=lunar_rotation()
    save(rotating,scenarios/"solar-system-moon-newton-dynamic-q2.json")
    (output/"Moon Rotation.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\n"runtime\\python.exe" -B -m solar_simulator gui "scenarios\\solar-system-moon-newton-dynamic-q2.json"\r\nif errorlevel 1 pause\r\n',encoding="ascii")
    from solar_simulator.application_profiles import solar_sandbox
    save(solar_sandbox(backend="rust"),scenarios/"solar-sandbox-eih-fixed-j2.json")
    (output/"Solar Sandbox.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\n"runtime\\python.exe" -B -m solar_simulator gui "scenarios\\solar-sandbox-eih-fixed-j2.json"\r\nif errorlevel 1 pause\r\n',encoding="ascii")
    shutil.copy2(ROOT/"docs/solar-sandbox-strict-checkpoint.json",scenarios/"solar-sandbox-strict.json")
    (output/"Solar Sandbox Strict.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\n"runtime\\python.exe" -B -m solar_simulator gui "scenarios\\solar-sandbox-strict.json"\r\nif errorlevel 1 pause\r\n',encoding="ascii")
    verification_export=subprocess.run([sys.executable,"-X","utf8","-B","-m","scripts.export_jpl_bundle",
        "--output",str(output/"verification")],cwd=ROOT,capture_output=True,text=True,encoding="utf-8")
    if verification_export.returncode:raise RuntimeError("Verification bundle export failed:\n"+verification_export.stderr)
    if not json.loads(verification_export.stdout)["checks_passed"]:raise RuntimeError("Exported JPL comparison failed")
    (output/"JPL Verification.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\n"runtime\\python.exe" -B -I "verification\\replay_jpl.py" "verification"\r\npause\r\n',encoding="ascii")
    (output/"Physics Verification.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\n"runtime\\python.exe" -B -I "verification\\recompute_jpl.py" "verification"\r\npause\r\n',encoding="ascii")
    (output/"Continuous Catalog Experimental.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\n"runtime\\python.exe" -X utf8 -B -I -m solar_simulator.continuous_cli --input "scenarios\\solar-system-asteroids-catalog-rust-1pn-solar-q2-relative.json" --target 720000 --packet-steps 20\r\npause\r\n',encoding="ascii")
    (output/"CURRENT-STATUS.md").write_text(
        "# Solar Simulator: текущая рабочая сборка\n\n"
        "Запуск приложения: `Solar Simulator.cmd`. Опыт со свободным вращением Луны: `Moon Rotation.cmd`.\n"
        "В окне доступна кнопка «Луна: свободное вращение» и вид Земля–Луна; остальные тела остаются в расчёте.\n"
        "Готовые настройки и сохранения находятся в `scenarios`; руководство — [USER-GUIDE](USER-GUIDE.md).\n\n"
        "Первая песочница: `Solar Sandbox.cmd` открывает10тел с EIH1PN и фиксированными J2 Солнца/Земли. "
        "`Solar Sandbox Strict.cmd` открывает отдельный профильrtol3e-14; "
        "[плотная квалификация и сохранённый отказ](docs/qualification-extension-validation.md). "
        "[Автономное сравнение и новый годовой расчёт](docs/verification-bundle-validation.md) "
        "запускаются отдельно: `JPL Verification.cmd` и `Physics Verification.cmd`. "
        "Расчёт до времени, ветки редактирования и добавление точечного тела доступны в окне. "
        "«Стоп и копия» и закрытие окна дожидаются пакета и сохраняют child+parent; "
        "«Recovery-копии…» открывает список локальных сохранений. "
        "[Порядок восстановления и ограничения](docs/controlled-stop.md). "
        "[Демонстрация](docs/sandbox-demo.md), [годовые измерения](docs/sandbox-demo-validation.md). "
        "Показатели относятся к исходной системе/годовой сетке, не к любым пользовательским системам.\n\n"
        f"Версия{project_version}: запись траектории и отдельный просмотр без расчёта, "
        "сравнение исходного и изменённого опыта на общих сохранённых временах, "
        "удобные единицы редактора и рецепт повторения. "
        f"[Состав версии и приёмка](docs/releases/v{project_version}.md). "
        "Принятие конкретного ZIP подтверждается отдельно результатом его проверки и SHA256.\n\n"
        "Отдельный экспериментальный расчёт354тел без анимации: `Continuous Catalog Experimental.cmd`; "
        "[Профильные проверки и непройденный общий критерий](docs/continuous-integration-validation.md).\n\n"
        "Вращение Луны — ньютоновская жёсткая solid-аппроксимация с обратными силами и моментами, "
        "с сохранением и продолжением q/S. Приливы, ядро и полная PN-модель вращения пока не включены. "
        "[Модель и ограничения](docs/nbody-rotation.md).\n\n"
        "Кольцо Койпера экспериментальное: вариант420тел не прошёл геометрическую проверку; "
        "528тел прошли заданные численные проверки, но остатки отдельных KBO выросли. "
        "Численное согласие не означает истинной физической точности.\n\n"
        "Новые проверки координат и тензорных моментов доступны в [отчёте карты](docs/harmonic-sphere-validation.md) "
        "и [отчёте тока](docs/chart-current-validation.md); эти исследовательские модели не подставлены "
        "в физическую инерцию Луны. Личные рабочие документы и исследовательский кеш не входят в сборку.\n",
        encoding="utf-8")
    manifest=dict(python=sys.version,python_abi=dll_name,project_version=project_version,rust_versions=rust_versions,
                  native_wheel=native_wheel.name,dependencies={name:d.version for name,d in dependencies.items()},
                  rotation_documents=rotation_documents,rotation_scenario="scenarios/solar-system-moon-newton-dynamic-q2.json",
                  desktop_features=["ready-lunar-rotation", "earth-moon-view", "worker-error-recovery", "visible-diagnostics",
                                    "localized-scenarios", "responsive-controls", "batched-orbit-rendering",
                                    "ready-solar-sandbox", "saved-experiment-branches", "add-point-body", "target-time-packets",
                                    "restore-immediate-parent", "remove-point-body", "sandbox-cli", "orbital-csv-provenance",
                                    "persistent-plot-artists", "qualified-strict-sandbox-profile", "offline-jpl-replay", "fresh-year-verification",
                                    "experimental-continuous-catalog-interval", "explicit-standard-strict-selection",
                                    "committed-packet-safe-close", "local-recovery-browser", "CLI-final-output-recovery",
                                    "recorded-trajectories", "independent-playback", "parent-child-comparison",
                                    "explicit-editor-units", "recording-recipes", "full-frame-replay"],
                  physical_PN_lunar_rotation_certified=False)
    (output/"BUILD-INFO.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    # Prove the copied runtime imports local packages and initializes real Tk.
    probe="import sys,pathlib,tkinter,solar_simulator,solar_native,numpy,matplotlib,scipy; from solar_simulator.experiment import advance,preset; r=tkinter.Tk(); r.withdraw(); r.destroy(); s=advance(preset('spheres',backend='rust'),2000); assert len(s.events)==2; from dataclasses import replace; a=preset('sun-earth'); a=replace(a,settings=replace(a.settings,integrator='dop853')); assert advance(a,20).time>0; assert len(advance(preset('solar-system'),20).bodies)==9; print(sys.prefix); print(pathlib.Path(solar_simulator.__file__).resolve()); print('portable Tk + native physics OK')"
    smoke="import tkinter; from solar_simulator.app import Laboratory; from solar_simulator.experiment import preset; r=tkinter.Tk(); r.withdraw(); a=Laboratory(r,preset('spheres',backend='rust')); a._start(); r.after(1000,a.close); r.mainloop(); print('portable application OK')"
    run_build_smokes(runtime/'python.exe',output,(probe,smoke))
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


def prepare_documents(output):
    """Prepare the same public documents for staging tests and actual builds."""
    import tomllib
    project_version=tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    documents=output/"docs"
    documents.mkdir()
    for name in ("physics.md","rust.md","user-guide.md","core-validation.md","core-validation.json","accuracy-validation.md","accuracy-validation.json","ephemerides.md","solar-system-reference.json","solar-system-validation.json","relativity.md","relativity-validation.json","moon.md","solar-system-moon-reference.json","moon-validation.json","oblateness.md","oblateness-validation.json","orientation.md","orientation-validation.json","orientation-spice-reference.json","relative-coordinates.md","relative-coordinates-validation.json","relative-checkpoint-validation.json","solar-j2.md","solar-j2-validation.json","solar-pole-validation.json","solar-checkpoint-validation.json"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    for name in ("pluto.md","pluto-reference.json","pluto-source-validation.json","pluto-validation.json","pluto-checkpoint-validation.json"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    for name in ("asteroids.md","body-data.md","asteroids-reference.json","asteroids-source-validation.json","asteroids-validation.json","asteroids-checkpoint-validation.json"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    for name in ("asteroids-full.md","asteroids-full-reference.json","asteroids-full-source-validation.json","asteroids-full-validation.json","asteroids-full-checkpoint-validation.json"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    for name in ("native-eih.md", "native-eih-validation.json"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    for name in ("error-control.md", "error-control-validation.json", "error-control-comparison.png"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    for name in ("orbit-observations.md", "orbit-observations-validation.json", "orbit-observations-residuals.png"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    for name in ("orbit-cohort.md", "orbit-cohort-manifest.json", "orbit-cohort-validation.json", "orbit-cohort-residuals.png"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    observation_data = output/"data"
    observation_data.mkdir()
    shutil.copy2(ROOT/"src/solar_simulator/data/orbit-observations-13270.json",observation_data/"orbit-observations-13270.json")
    for path in (ROOT/"src/solar_simulator/data").glob("orbit-cohort-*.json"):
        shutil.copy2(path,observation_data/path.name)
    (output/"scripts").mkdir()
    shutil.copy2(ROOT/"scripts/orbit-cohort-policy.json",output/"scripts/orbit-cohort-policy.json")
    for name in ("asteroids-catalog.md", "asteroids-catalog-validation.json", "asteroids-catalog-comparison.png"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    for name in ("asteroids-343.md", "asteroids-343-initial.json", "asteroids-343-source-validation.json", "asteroids-343-assessment.json"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    for name in ("kuiper.md", "kuiper-ring-design.md", "kuiper-initial.json", "kuiper-source-validation.json", "kuiper-validation.json", "kuiper-absolute-reference-validation.json", "kuiper-comparison.png", "perturber-audit.md", "perturber-audit.json"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    for name in ("kuiper-ring.md", "kuiper-ring-validation.json", "kuiper-ring-refinement-validation.json", "kuiper-ring-field-validation.json", "kuiper-ring-kbo-validation.json", "kuiper-ring-comparison.png"):
        shutil.copy2(ROOT/"docs"/name,documents/name)
    shutil.copy2(ROOT/"scripts/kuiper-ring-policy.json",output/"scripts/kuiper-ring-policy.json")
    shutil.copy2(ROOT/"scripts/kuiper-ring-refinement-policy.json",output/"scripts/kuiper-ring-refinement-policy.json")
    shutil.copy2(ROOT/"scripts/sb441-kuiper-ranges.json",output/"scripts/sb441-kuiper-ranges.json")
    shutil.copy2(ROOT/"scripts/de441-perturber-catalog.json",output/"scripts/de441-perturber-catalog.json")
    (output/"scripts/validation").mkdir()
    shutil.copy2(ROOT/"scripts/sb441-343-ranges.json",output/"scripts/sb441-343-ranges.json")
    shutil.copy2(ROOT/"scripts/validation/sb441-343-year.bin",output/"scripts/validation/sb441-343-year.bin")
    shutil.copy2(ROOT/"scripts/validation/de441-header.441",output/"scripts/validation/de441-header.441")
    shutil.copy2(ROOT/"scripts/validation/kuiper_absolute_assessment.py",output/"scripts/validation/kuiper_absolute_assessment.py")
    rotation_documents=copy_public_rotation_documents(output,extra_seeds=("user-guide.md","physics.md","rust.md","runtime-walkthrough.md","desktop-render-benchmark.md",
        "sandbox-models-validation.md","sandbox-experiments.md","time-control-validation.md",
        "sandbox-demo-validation.md","sandbox-demo.md","sandbox-controls.md","runtime-performance-validation.md",
        "qualification-extension-validation.md", "verification-bundle-validation.md",
        "continuous-integration-validation.md", f"releases/v{project_version}.md"))
    orientation_doc=documents/"orientation.md"
    orientation_doc.write_text(orientation_doc.read_text(encoding="utf-8").replace(
        "../src/solar_simulator/data/ERFA-LICENSE.txt",
        "../runtime/Lib/site-packages/solar_simulator/data/ERFA-LICENSE.txt"),encoding="utf-8")
    for source,target in (("user-guide.md","USER-GUIDE.md"),("physics.md","PHYSICS.md")):
        export_guide(documents/source,output/target)
    return rotation_documents


def copy_public_rotation_documents(output,extra_seeds=()):
    """Copy the public rotation/report link closure, excluding personal files.

    Only documentation/assets and JSON policies are included; local research
    caches, source-code line links and personal documents stay in the project.
    """
    import re
    private={"AGENTS.md","changes.md","development-plan.md","learning-log.md","project-review.md",
             "session-handoff.md","session-handoff-archive.md","project-context.md"}
    seeds=("nbody-rotation.md","rotation-year.md","lunar-spin-initial.md","conservative-rotation.md",
           "harmonic-sphere-validation.md","chart-current-validation.md")+tuple(extra_seeds)
    pending=deque((ROOT/"docs"/name).resolve() for name in seeds);copied=set()
    destination_root=Path(output).resolve()
    while pending:
        source=pending.popleft()
        if source in copied:continue
        if not source.is_relative_to(ROOT.resolve()) or source.name in private or '.tools' in source.parts:
            raise ValueError('Nonpublic portable document: '+str(source))
        relative=source.relative_to(ROOT.resolve())
        allowed=((relative.parts[0]=='docs' and (source.suffix in {'.md','.json','.png','.txt'}
                  or source.name=='continuous-integration-reference.npz'))
                 or (relative.parts[0]=='scripts' and source.suffix=='.json')
                 or relative.as_posix()=='src/solar_simulator/data/ERFA-LICENSE.txt'
                 or relative.as_posix() in PUBLIC_DOCUMENT_ARCHIVES)
        if not allowed:raise ValueError('Unsupported portable document: '+str(relative))
        if not source.is_file():raise FileNotFoundError('Public rotation document unavailable: '+str(relative))
        target=destination_root/relative;target.parent.mkdir(parents=True,exist_ok=True)
        if source.suffix=='.md':
            text=source.read_text(encoding='utf-8')
            def local_link(match):
                label,name=match.group(1),match.group(2);raw=name.split('#',1)[0].strip('<>')
                if not raw or ':' in raw:return match.group(0)
                candidate=(source.parent/raw).resolve()
                if candidate.name in private or '.tools' in candidate.parts:return label
                if candidate.suffix in {'.md','.json','.png','.txt','.zip'} or candidate.name=='continuous-integration-reference.npz':pending.append(candidate)
                return match.group(0)
            text=re.sub(r'\[([^\]]*)\]\(([^)]+)\)',local_link,text)
            target.write_text(text,encoding='utf-8')
        else:shutil.copy2(source,target)
        copied.add(source)
    return sorted(path.relative_to(ROOT.resolve()).as_posix() for path in copied)


def export_guide(source,target):
    """Rebase every relative Markdown asset from docs/ to the exported guide."""
    import os
    import re
    def rebase(match):
        label,link=match.group(1),match.group(2)
        raw,separator,fragment=link.partition('#')
        if not raw or ':' in raw:return match.group(0)
        relative=Path(os.path.relpath(source.parent/raw.strip('<>'),target.parent)).as_posix()
        return f'[{label}]({relative}{separator}{fragment})'
    target.write_text(re.sub(r'\[([^\]]*)\]\(([^)]+)\)',rebase,source.read_text(encoding='utf-8')),
                      encoding='utf-8')


if __name__=="__main__":
    build()
