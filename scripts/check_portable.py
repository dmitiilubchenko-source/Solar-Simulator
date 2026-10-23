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
        private={"AGENTS.md","changes.md","development-plan.md","learning-log.md","project-review.md",
                 "session-handoff.md","session-handoff-archive.md","project-context.md"}
        for member in archive.infolist():
            if not (target/member.filename).resolve().is_relative_to(target.resolve()):
                raise ValueError("Unsafe ZIP path")
            parts=Path(member.filename).parts
            if Path(member.filename).name in private or ".tools" in parts:
                raise ValueError("Private file in portable ZIP: "+member.filename)
        archive.extractall(target)
    folder=next(p for p in target.iterdir() if p.is_dir())
    document_links=check_document_links(folder)
    runtime=folder/"runtime"
    probe="""
import json,pathlib,sys,tkinter,solar_native,numpy,matplotlib,scipy,solar_simulator
from importlib.metadata import version
from packaging.version import Version
build=json.loads(pathlib.Path('BUILD-INFO.json').read_bytes())
assert version('solar-simulator')==build['project_version']
assert Version(version('solar-native'))==Version(build['rust_versions']['solar_native'])
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
dynamic=load('scenarios/solar-system-moon-newton-dynamic-q2.json')
assert len(dynamic.rotations)==1 and dynamic.rotations[0].body=='Moon'
assert dynamic.settings.physics=='newtonian' and dynamic.settings.relative_pair==('Earth','Moon')
assert dynamic.settings.integrator=='dop853' and dynamic.settings.error_control=='per-body'
dynamic=advance(dynamic,2)
save(dynamic,'checkpoint-dynamic-rotation-test.json')
dynamic_restored=load('checkpoint-dynamic-rotation-test.json')
assert dynamic_restored.rotations==dynamic.rotations and dynamic_restored.initial_rotations==dynamic.initial_rotations
assert dynamic_restored.settings==dynamic.settings and dynamic_restored.origin==dynamic.origin
assert advance(dynamic_restored,2).time==4*dynamic.settings.dt
assert len(report(dynamic)['rotations'])==1 and 'orbital+rigid-spin' in report(dynamic)['conservation_scope']
assert 'no tides/EIH' in report(dynamic)['conservation_scope']
assert dynamic.rotations[0].quaternion!=dynamic.initial_rotations[0].quaternion
assert pathlib.Path('docs/nbody-rotation.md').is_file() and pathlib.Path('Moon Rotation.cmd').is_file()
assert '(docs/nbody-rotation.md)' in pathlib.Path('USER-GUIDE.md').read_text(encoding='utf-8')
assert pathlib.Path('CURRENT-STATUS.md').is_file()
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
pluto=advance(load('scenarios/solar-system-pluto-1pn-solar-q2-relative.json'),24)
assert len(pluto.bodies)==11 and pluto.bodies[-1].name=='Pluto-System'
assert pluto.settings.rtol==3e-14 and len(pluto.settings.figures)==3 and pluto.orientation_work!=0
save(pluto,'checkpoint-pluto-test.json')
pluto_restored=load('checkpoint-pluto-test.json')
assert pluto_restored.origin==pluto.origin and pluto_restored.settings.figures==pluto.settings.figures
assert advance(pluto_restored,24).time==172800
asteroids=advance(load('scenarios/solar-system-asteroids-1pn-solar-q2-relative.json'),24)
assert len(asteroids.bodies)==14 and [b.name for b in asteroids.bodies[11:]]==['Ceres','Pallas','Vesta']
assert len(asteroids.settings.figures)==3 and asteroids.settings.relative_pair==('Earth','Moon')
save(asteroids,'checkpoint-asteroids-test.json')
asteroids_restored=load('checkpoint-asteroids-test.json')
assert asteroids_restored.origin==asteroids.origin and asteroids_restored.orientation_work==asteroids.orientation_work
assert advance(asteroids_restored,24).time==172800
assert len(advance(preset('solar-system-asteroids',backend='rust'),1).bodies)==14
full=advance(load('scenarios/solar-system-asteroids-full-1pn-solar-q2-relative.json'),24)
assert len(full.bodies)==27 and len(full.settings.figures)==3 and full.orientation_work!=0
save(full,'checkpoint-asteroids-full-test.json')
full_restored=load('checkpoint-asteroids-full-test.json')
assert full_restored.origin==full.origin and full_restored.orientation_work==full.orientation_work
assert advance(full_restored,24).time==172800
assert len(advance(preset('solar-system-asteroids-full',backend='rust'),1).bodies)==27
native_pn=advance(load('scenarios/solar-system-asteroids-full-rust-1pn-solar-q2-relative.json'),24)
assert native_pn.settings.backend=='rust' and native_pn.settings.integrator=='dop853'
assert native_pn.settings.physics=='eih-1pn' and native_pn.orientation_work!=0
import numpy as np
assert max(np.linalg.norm(np.array([a.position.x,a.position.y,a.position.z])-np.array([b.position.x,b.position.y,b.position.z]))
    for a,b in zip(native_pn.bodies,full.bodies))<.01
save(native_pn,'checkpoint-native-pn-test.json')
restored_native=load('checkpoint-native-pn-test.json')
assert restored_native.settings==native_pn.settings and restored_native.orientation_work==native_pn.orientation_work
assert advance(restored_native,24).time==172800
catalogue=advance(load('scenarios/solar-system-asteroids-catalog-rust-1pn-solar-q2-relative.json'),4)
assert len(catalogue.bodies)==354 and catalogue.settings.backend=='rust'
assert catalogue.settings.physics=='eih-1pn' and catalogue.settings.integrator=='dop853'
assert catalogue.settings.relative_pair==('Earth','Moon') and len(catalogue.settings.figures)==3
assert catalogue.settings.error_control=='per-body'
assert catalogue.settings.position_atol==1e-7 and catalogue.settings.velocity_atol==1e-13
assert catalogue.orientation_work!=0
save(catalogue,'checkpoint-catalogue-test.json')
restored_catalogue=load('checkpoint-catalogue-test.json')
assert restored_catalogue.origin==catalogue.origin and restored_catalogue.orientation_work==catalogue.orientation_work
assert restored_catalogue.settings.error_control=='per-body'
assert advance(restored_catalogue,4).time==28800
kuiper=advance(load('scenarios/solar-system-kuiper-rust-1pn-solar-q2-relative.json'),4)
assert len(kuiper.bodies)==384 and kuiper.settings.backend=='rust'
assert kuiper.settings.physics=='eih-1pn' and kuiper.settings.relative_pair==('Earth','Moon')
assert len(kuiper.settings.figures)==3 and kuiper.settings.error_control=='per-body'
assert kuiper.settings.position_atol==1e-7 and kuiper.settings.velocity_atol==1e-13
assert kuiper.orientation_work!=0
save(kuiper,'checkpoint-kuiper-test.json')
restored_kuiper=load('checkpoint-kuiper-test.json')
assert restored_kuiper.origin==kuiper.origin and restored_kuiper.settings==kuiper.settings
assert advance(restored_kuiper,4).time==28800
ring=advance(load('scenarios/solar-system-kuiper-ring-rust-1pn-solar-q2-relative.json'),4)
assert len(ring.bodies)==420 and ring.settings.backend=='rust' and ring.settings.physics=='eih-1pn'
assert ring.settings.relative_pair==('Earth','Moon') and len(ring.settings.figures)==3
assert ring.settings.error_control=='per-body' and ring.settings.position_atol==1e-7
assert ring.orientation_work!=0
save(ring,'checkpoint-ring-test.json')
restored_ring=load('checkpoint-ring-test.json')
assert restored_ring.origin==ring.origin and restored_ring.settings==ring.settings
assert advance(restored_ring,4).time==28800
refined=advance(load('scenarios/solar-system-kuiper-ring-144-rust-1pn-solar-q2-relative.json'),4)
assert len(refined.bodies)==528 and refined.settings.backend=='rust'
assert refined.settings.physics=='eih-1pn' and refined.settings.relative_pair==('Earth','Moon')
assert refined.settings.error_control=='per-body' and len(refined.settings.figures)==3
save(refined,'checkpoint-refined-ring-test.json')
restored_refined=load('checkpoint-refined-ring-test.json')
assert restored_refined.origin==refined.origin and restored_refined.settings==refined.settings
assert advance(restored_refined,4).time==28800
solar=advance(load('scenarios/solar-system-moon-1pn-solar-q2-relative.json'),24)
assert len(solar.settings.figures)==3 and solar.settings.figures[0].body=='Sun'
assert solar.settings.relative_pair==('Earth','Moon') and solar.orientation_work!=0
save(solar,'checkpoint-solar-test.json')
solar_restored=load('checkpoint-solar-test.json')
assert solar_restored.settings.figures==solar.settings.figures and solar_restored.orientation_work==solar.orientation_work
assert advance(solar_restored,24).time==172800
sun_only=advance(load('scenarios/solar-system-1pn-solar-j2.json'),24)
assert len(sun_only.settings.figures)==1 and sun_only.settings.figures[0].body=='Sun' and sun_only.orientation_work==0
pair=advance(load('scenarios/solar-system-moon-1pn-q2-relative.json'),24)
assert pair.settings.relative_pair==('Earth','Moon') and pair.orientation_work!=0
save(pair,'checkpoint-pair-test.json')
restored=load('checkpoint-pair-test.json')
assert restored.settings.relative_pair==pair.settings.relative_pair and restored.orientation_work==pair.orientation_work
assert advance(restored,24).time==172800
from importlib.resources import files
assert 'NumFOCUS' in files('solar_simulator.data').joinpath('ERFA-LICENSE.txt').read_text()
from solar_simulator.cli import main
import contextlib,io
with contextlib.redirect_stdout(io.StringIO()):
    assert main(['fit-orbit','data/orbit-observations-13270.json','orbit-report.json'])==0
orbit_report=json.loads(pathlib.Path('orbit-report.json').read_text(encoding='utf-8'))
assert orbit_report['fit']['rank']==6 and orbit_report['holdout']['count']==24
assert orbit_report['holdout']['rms_arcsec']<.8
with contextlib.redirect_stdout(io.StringIO()):
    assert main(['fit-orbit','data/orbit-cohort-13270.json','cohort-report.json'])==0
cohort_report=json.loads(pathlib.Path('cohort-report.json').read_text(encoding='utf-8'))
assert cohort_report['fit']['error_model']['night_systematic_arcsec']==.15
assert cohort_report['holdout']['count']==99 and cohort_report['holdout']['rms_arcsec']<1
assert cohort_report['holdout_coverage']['station_night_count']==24
print(json.dumps(dict(prefix=str(root),tcl=str(library),events=len(experiment.events),isolated=sys.flags.isolated)))
"""
    environment=os.environ.copy()
    windows=Path(os.environ["SystemRoot"])
    environment["PATH"]=str(windows/"System32")+os.pathsep+str(windows)
    for name in ("PYTHONHOME","PYTHONPATH","TCL_LIBRARY","TK_LIBRARY"):
        environment.pop(name,None)
    environment['LOCALAPPDATA']=str(target/'isolated user data')
    output=subprocess.check_output([str(runtime/"python.exe"),"-B","-I","-c",probe],cwd=folder,text=True,env=environment)
    result=json.loads(output)
    result['document_links']=document_links
    result["gui"]=check_gui(folder,environment)
    result['recovery']=check_recovery(folder,environment)
    result['recording_workflows']=check_recording_workflows(folder,environment)
    patch_script=Path(__file__).with_name('portable_patch_workflows.py')
    patch_environment={**environment,'LOCALAPPDATA':str(folder/'patch031 user data'),
                       'MPLCONFIGDIR':str(folder/'patch031 matplotlib')}
    patch_process=subprocess.run([str(runtime/'python.exe'),'-X','utf8','-B','-I',str(patch_script)],
        cwd=folder,env=patch_environment,capture_output=True,text=True,encoding='utf-8',timeout=120)
    if patch_process.returncode:
        raise RuntimeError('Relocated patch workflows failed:\n'+patch_process.stdout+patch_process.stderr)
    result['patch031_workflows']=json.loads(patch_process.stdout)
    if result['patch031_workflows']['isolated']!=1:
        raise ValueError('Patch workflows must use isolated runtime')
    replay_output=subprocess.check_output([str(runtime/"python.exe"),"-X","utf8","-B","-I",
        str(folder/"verification/replay_jpl.py"),str(folder/"verification")],cwd=folder,env=environment,text=True,encoding="utf-8")
    result["jpl_replay"]=json.loads(replay_output)
    if not result["jpl_replay"]["checks_passed"] or result["jpl_replay"]["solver_executed"]:
        raise ValueError("Replay scope or results failed")
    fresh_output=subprocess.check_output([str(runtime/"python.exe"),"-X","utf8","-B","-I",
        str(folder/"verification/recompute_jpl.py"),str(folder/"verification"),
        "--output",str(folder/"fresh-year-verification.json")],cwd=folder,env=environment,text=True,encoding="utf-8")
    result["fresh_year"]=json.loads(fresh_output)
    if not result["fresh_year"]["checks_passed"] or not result["fresh_year"]["solver_executed"]:
        raise ValueError("Fresh production propagation failed")
    result["continuous"]=check_continuous(folder,environment)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print(f"RELOCATED_DIR={folder}")


def check_recovery(folder,environment):
    """Save/close and restore/continue in separate isolated runtime processes."""
    create=r'''
import json,pathlib,time,tkinter
from dataclasses import replace
from solar_simulator.app import Laboratory
from solar_simulator.branch_io import save_experiment
from solar_simulator.experiment import advance,preset
from solar_simulator.sandbox import branch_experiment
paths={}
for backend in ('python','rust'):
    seed=preset('sun-earth',backend=backend)
    seed=replace(seed,settings=replace(seed.settings,integrator='dop853'))
    parent=advance(seed,2)
    body=replace(parent.bodies[0],mass=parent.bodies[0].mass*1.1)
    branch=branch_experiment(parent,replacements=((body.name,body),))
    expected=advance(branch.child,2)
    save_experiment(expected,f'recovery-expected-{backend}.json',parent_snapshot=branch.parent_snapshot)
    window=tkinter.Tk();window.withdraw()
    app=Laboratory(window,branch.child,parent_snapshot=branch.parent_snapshot)
    app._submit(2);app._request_close()
    deadline=time.monotonic()+20
    while not app.closed and time.monotonic()<deadline:
        window.update();time.sleep(.01)
    assert app.closed and app.last_recovery_path.is_file()
    paths[backend]=str(app.last_recovery_path)
pathlib.Path('recovery-stage.json').write_text(json.dumps(paths),encoding='utf-8')
print(json.dumps(dict(saved=list(paths))))
'''
    restore=r'''
import contextlib,io,json,pathlib,sys,tkinter
from tkinter import ttk
from solar_simulator.app import Laboratory
from solar_simulator.branch_io import open_experiment
from solar_simulator.experiment import advance
from solar_simulator.storage import to_document
from solar_simulator.commands import main
paths=json.loads(pathlib.Path('recovery-stage.json').read_bytes())
results={}
for backend,path in paths.items():
    window=tkinter.Tk();window.withdraw();app=Laboratory(window)
    try:
        expected,parent=open_experiment(f'recovery-expected-{backend}.json')
        actual,actual_parent=open_experiment(path)
        assert to_document(actual)==to_document(expected) and actual_parent==parent
        dialog=app._show_recoveries()
        tree=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
        item=next(i for i in tree.get_children() if tree.item(i,'values')[0]==pathlib.Path(path).parent.name)
        tree.selection_set(item)
        button=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')=='Открыть выбранную копию')
        button.invoke()
        assert not dialog.winfo_exists()
        assert to_document(app.experiment)==to_document(expected) and app.parent_snapshot==parent
        continued=advance(expected,2)
        app._submit(2);app.future.result(timeout=20);app._poll()
        assert to_document(app.experiment)==to_document(continued) and app.parent_snapshot==parent
        app._request_close()
        saved,saved_parent=open_experiment(app.last_recovery_path)
        assert to_document(saved)==to_document(continued) and saved_parent==parent
        results[backend]=dict(time_seconds=continued.time,parent_preserved=True,exact_continuation=True)
    finally:
        if not app.closed:app.close()
source=paths['rust'];initial,parent=open_experiment(source)
expected=advance(initial,1)
for destination,fallback in ((pathlib.Path('absent output')/'out.json',False),
                             (pathlib.Path('blocked output')/'out.json',True)):
    if fallback:destination.parent.write_bytes(b'keep blocker')
    stderr=io.StringIO();stdout=io.StringIO()
    with contextlib.redirect_stderr(stderr),contextlib.redirect_stdout(stdout):
        try:main(['run-until',source,str(destination),'--time',str(expected.time)])
        except SystemExit as error:assert error.code==2
        else:raise AssertionError('Expected final output failure')
    diagnostic=json.loads(stderr.getvalue().splitlines()[0])
    child,recovered_parent=open_experiment(diagnostic['recovery_path'])
    assert to_document(child)==to_document(expected) and recovered_parent==parent
    assert diagnostic['target_reached'] and diagnostic['recovery_fallback']==fallback
    assert not destination.exists() and not stdout.getvalue()
print(json.dumps(dict(isolated=sys.flags.isolated,restart=results,CLI_finished_result_recovered=True,CLI_local_fallback=True)))
'''
    for name,probe in (('create',create),('restore',restore)):
        process=subprocess.run([str(folder/'runtime/python.exe'),'-X','utf8','-B','-I','-c',probe],
            cwd=folder,env=environment,capture_output=True,text=True,encoding='utf-8',timeout=60)
        if process.returncode:raise RuntimeError(f'Relocated recovery {name} failed:\n'+process.stdout+process.stderr)
    result=json.loads(process.stdout)
    if result['isolated']!=1:raise ValueError('Recovery must use an isolated runtime')
    return result


def check_recording_workflows(folder,environment):
    """Exercise the actual extracted package across independent process lifetimes."""
    script=Path(__file__).with_name('portable_workflows.py')
    results={}
    for phase in ('create','restore'):
        process=subprocess.run([str(folder/'runtime/python.exe'),'-X','utf8','-B','-I',str(script),phase],
            cwd=folder,env=environment,capture_output=True,text=True,encoding='utf-8',timeout=240)
        if process.returncode:
            raise RuntimeError(f'Relocated recording {phase} failed:\n'+process.stdout+process.stderr)
        results[phase]=json.loads(process.stdout)
        if results[phase]['isolated']!=1:
            raise ValueError('Recording acceptance must use an isolated interpreter')
    return results


def check_document_links(folder):
    """Validate actual packaged relative Markdown targets before launching Python."""
    import re
    count=0
    root=Path(folder).resolve()
    for path in root.rglob('*.md'):
        if 'runtime' in path.relative_to(root).parts:continue
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            raw=link.split('#',1)[0].strip('<>')
            if not raw or ':' in raw:continue
            target=(path.parent/raw).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                raise ValueError(f'Broken portable document link: {path.relative_to(root)} -> {link}')
            count+=1
    return count


def check_gui(folder,environment):
    """A separate Tcl process checks the actual desktop path after relocation."""
    probe=r'''
import json,pathlib,sys,time,tkinter
import solar_simulator.app as application
from solar_simulator.storage import load,to_document
from solar_simulator.experiment import advance
from solar_simulator.time_control import advance_towards
window=tkinter.Tk(); app=application.Laboratory(window); errors=[]
application.messagebox.showerror=lambda *args,**kwargs:errors.append(args)
def wait_for_worker():
    deadline=time.monotonic()+20
    while app.future is not None and time.monotonic()<deadline:
        window.update(); time.sleep(.01)
    assert app.future is None and not errors,(app.future,errors)
try:
    app._open_lunar_rotation()
    window.update()
    bottom=window.winfo_rooty()+window.winfo_height()
    for label in (app.status_widget,app.details_widget):
        assert label.winfo_ismapped() and label.winfo_rooty()+label.winfo_height()<=bottom
    window.withdraw()
    original=to_document(app.experiment)
    assert original==to_document(load('scenarios/solar-system-moon-newton-dynamic-q2.json'))
    assert app.view.get()=='Земля и Луна' and app.reference.get()=='Тело: Earth'
    assert len(app.experiment.bodies)==10 and len(app.orbit.get_legend().get_texts())==2
    app._submit(2); app._pause()
    assert 'завершает пакет' in app.status.get()
    wait_for_worker()
    assert app.experiment.time==7200 and 'Полный L' in app.details.get()
    checkpoint=to_document(app.experiment)
    path=pathlib.Path('Контрольная точка Луны.json').resolve()
    application.filedialog.asksaveasfilename=lambda **kwargs:str(path)
    app._save(); assert to_document(load(path))==checkpoint
    app._reset(); assert to_document(app.experiment)==original
    application.filedialog.askopenfilename=lambda **kwargs:str(path)
    app._load(); assert to_document(app.experiment)==checkpoint
    expected=to_document(advance(load(path),1))
    app._submit(1); wait_for_worker(); assert to_document(app.experiment)==expected
    app.scenario.set('spheres'); app.scenario_widget.event_generate('<<ComboboxSelected>>')
    window.update(); app._new()
    assert app.integrator.get()=='verlet' and app.mode.get()=='bounce'
    app._submit(2); wait_for_worker(); assert app.experiment.time==.1
    contacts_time=app.experiment.time
    assert app.solar_profile.get()=='strict'
    app.solar_profile.set('standard')
    app.backend.set('rust'); app._open_solar_sandbox()
    sandbox_start=to_document(app.experiment)
    assert sandbox_start==to_document(load('scenarios/solar-sandbox-eih-fixed-j2.json'))
    assert pathlib.Path('Solar Sandbox.cmd').is_file()
    assert pathlib.Path('docs/sandbox-demo-validation.json').is_file()
    app.batch.set('2'); app.target.set('10000.25'); app._start_target()
    app._poll(); app._pause(); wait_for_worker()
    assert app.experiment.time==7200 and not app.running
    application.filedialog.asksaveasfilename=lambda **kwargs:str(path)
    app._save(); checkpoint_solar=to_document(app.experiment)
    app._reset(); app._load()
    assert to_document(app.experiment)==checkpoint_solar and app.target_time is None
    app._start_target()
    deadline=time.monotonic()+20
    while (app.running or app.future is not None) and time.monotonic()<deadline:
        window.update(); time.sleep(.01)
    assert not app.running and app.future is None and not errors
    assert app.experiment.time==10000.25
    expected_solar=advance_towards(load(path),10000.25,2)
    assert to_document(app.experiment)==to_document(expected_solar)
    # Drive the actual add dialog and compare its saved child with the core API.
    from solar_simulator.sandbox import branch_experiment,load_branch
    from solar_simulator.simulation import Body,EARTH_MASS
    from solar_simulator.vector3 import Vector3
    parent=app.experiment
    addition=Body('Demo planet',EARTH_MASS,Vector3(0.,0.,3e11),Vector3(17000.,0.,0.))
    expected_branch=branch_experiment(parent,additions=(addition,))
    branch_path=pathlib.Path('Ветка новой планеты.json').resolve()
    application.filedialog.asksaveasfilename=lambda **kwargs:str(branch_path)
    app._add_body(); window.update()
    dialog=next(widget for widget in window.winfo_children() if isinstance(widget,tkinter.Toplevel))
    entries=[]; buttons=[]
    def collect(widget):
        for child in widget.winfo_children():
            if type(child) is application.ttk.Entry:entries.append(child)
            if isinstance(child,application.ttk.Button):buttons.append(child)
            collect(child)
    collect(dialog)
    assert len(entries)==8
    for entry,value in zip(entries,('Demo planet',str(EARTH_MASS),'0','0','3e11','17000','0','0')):
        entry.delete(0,'end');entry.insert(0,value)
    next(button for button in buttons if 'Сохранить и добавить' in button.cget('text')).invoke()
    assert not errors and app.experiment.time==0 and len(app.experiment.bodies)==11
    saved=load_branch(branch_path)
    assert to_document(saved.parent)==to_document(parent)
    assert to_document(saved.child)==to_document(expected_branch.child)==to_document(app.experiment)
    assert app.parent_snapshot==saved.parent_snapshot
    child_path=pathlib.Path('Дочерний опыт перед возвратом.json').resolve()
    application.filedialog.asksaveasfilename=lambda **kwargs:str(child_path)
    child_before=to_document(app.experiment)
    app._restore_parent()
    preserved=load_branch(child_path)
    assert to_document(preserved.child)==child_before and preserved.parent_snapshot==saved.parent_snapshot
    assert to_document(app.experiment)==to_document(parent) and app.parent_snapshot is None
    app.scenario.set('sun-earth');app._select_scenario();app._new()
    removal_parent=app.experiment
    removal_path=pathlib.Path('Удалённое Солнце.json').resolve()
    application.filedialog.asksaveasfilename=lambda **kwargs:str(removal_path)
    app._remove_body();window.update()
    dialog=next(w for w in window.winfo_children() if isinstance(w,tkinter.Toplevel))
    choice=next(w for w in dialog.winfo_children() if isinstance(w,application.ttk.Combobox));choice.set('Sun')
    next(w for w in dialog.winfo_children() if isinstance(w,application.ttk.Button)).invoke()
    assert not errors and len(app.experiment.bodies)==1 and app.experiment.bodies[0].name=='Earth'
    assert to_document(load_branch(removal_path).parent)==to_document(removal_parent)
    expected_free=advance(app.experiment,1);app._submit(1);wait_for_worker()
    assert to_document(app.experiment)==to_document(expected_free)
    csv_input=pathlib.Path('CSV source.json');csv_output=pathlib.Path('Orbit slice.csv')
    application.save_experiment(app.experiment,csv_input,parent_snapshot=app.parent_snapshot)
    import subprocess,csv
    exported=subprocess.run([sys.executable,'-B','-I','-m','solar_simulator','export-state',str(csv_input),str(csv_output)],
                            capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert exported.returncode==0,exported.stderr
    with csv_output.open(encoding='utf-8',newline='') as stream:row=next(csv.DictReader(stream))
    assert row['name']=='Earth' and float(row['time_seconds'])==app.experiment.time
    import hashlib
    strict_path=pathlib.Path('scenarios/solar-sandbox-strict.json').resolve()
    strict_receipt=json.loads(pathlib.Path('docs/strict-profile-validation.json').read_bytes())
    assert pathlib.Path('Solar Sandbox Strict.cmd').is_file()
    assert hashlib.sha256(strict_path.read_bytes()).hexdigest()==strict_receipt['checkpoint_sha256']
    strict=load(strict_path)
    assert strict.settings.rtol==3e-14 and strict.settings.backend=='rust' and len(strict.bodies)==10
    application.filedialog.askopenfilename=lambda **kwargs:str(strict_path)
    app._load()
    assert to_document(app.experiment)==to_document(strict) and float(app.rtol.get())==3e-14
    app.solar_profile.set('strict');app._open_solar_sandbox()
    assert to_document(app.experiment)==to_document(strict)
    from solar_simulator.time_control import advance_towards
    expected_strict=advance_towards(strict,10000.25)
    app.batch.set('20');app.target.set('10000.25');app._start_target()
    deadline=time.monotonic()+20
    while (app.running or app.future is not None) and time.monotonic()<deadline:
        window.update();time.sleep(.01)
    assert not errors and app.experiment.time==10000.25
    assert to_document(app.experiment)==to_document(expected_strict)
    result=dict(isolated=sys.flags.isolated,moon_checkpoint_time_s=checkpoint['time'],
                moon_continuation_time_s=expected['time'],contacts_scenario_time_s=contacts_time,
                footer_visible=True,GUI_save_load_reset_continue=True,
                solar_target_time_s=expected_solar.time,solar_target_pause_save_resume=True,
                GUI_add_body_saved_parent=True,GUI_parent_restore_saved_child=True,
                GUI_remove_sun_free_motion=True,isolated_CLI_CSV=True,
                strict_checkpoint_sha256=True,GUI_strict_load_and_exact_target=True)
finally:
    app.close()
print(json.dumps(result))
'''
    result=subprocess.run([str(folder/"runtime/python.exe"),"-B","-I","-c",probe],
                          cwd=folder,env=environment,capture_output=True,text=True,timeout=60)
    if result.returncode:
        raise RuntimeError("Relocated GUI failed:\n"+result.stdout+result.stderr)
    report=json.loads(result.stdout)
    if report["isolated"] != 1:
        raise ValueError("Relocated GUI must use an isolated runtime")
    return report


def check_continuous(folder,environment):
    """Recompute explicit profiles from the actual relocated package."""
    probe=r'''
import csv,hashlib,json,pathlib,numpy as np,sys
from solar_simulator.continuous_cli import run
from solar_simulator.continuous import ContinuousRun
from solar_simulator.storage import load
root=pathlib.Path.cwd()
receipt=json.loads((root/'docs/continuous-integration-validation.json').read_bytes())
path=root/'docs/continuous-integration-reference.npz'
assert hashlib.sha256(path.read_bytes()).hexdigest()==receipt['public_reference_sha256']
with np.load(path,allow_pickle=False) as data:
    sample={k:data[k].copy() for k in data.files}
def matrix(state):
    return np.array([[b.position.x,b.position.y,b.position.z,b.velocity.x,b.velocity.y,b.velocity.z] for b in state.bodies])
def difference(actual,expected):
    return dict(position_metres=float(np.max(np.linalg.norm(actual[...,:3]-expected[...,:3],axis=-1))),
                velocity_m_per_s=float(np.max(np.linalg.norm(actual[...,3:]-expected[...,3:],axis=-1))))
result=run(root/'scenarios/solar-system-asteroids-catalog-rust-1pn-solar-q2-relative.json',720000.,
           root/'continuous-catalog-check',packet_steps=20)
assert result['sample_times_seconds']==sample['catalog_times'].tolist()
assert result['experimental'] and not result['automatically_scientifically_qualified']
rows=list(csv.DictReader((root/'continuous-catalog-check/snapshots.csv').open(encoding='utf-8')))
assert len(rows)==3894
actual=np.array([[float(row[k]) for k in ('x_m','y_m','z_m','vx_m_s','vy_m_s','vz_m_s')] for row in rows]).reshape(11,354,6)
catalog=difference(actual,sample['catalog_continuous'])
assert catalog['position_metres']<.1 and catalog['velocity_m_per_s']<1e-6
seed=load(root/'scenarios/solar-sandbox-strict.json')
session=ContinuousRun(seed,float(sample['year_times'][-1]));values=[]
for time in sample['year_times']:
    while session.current.time<time:session.next(20,until=float(time))
    values.append(matrix(session.current))
actual=np.array(values)
year=difference(actual,sample['year_continuous'])
relative=difference(actual[:,4]-actual[:,3],sample['year_independent'][:,4]-sample['year_independent'][:,3])
assert year['position_metres']<.1 and year['velocity_m_per_s']<1e-6
assert relative['position_metres']<.1 and relative['velocity_m_per_s']<1e-5
assert receipt['general_release_passed'] is False
print(json.dumps(dict(catalog_reproduction=catalog,year_reproduction=year,relative_independent=relative,
    catalog_rhs_calls=result['rhs_calls'],catalog_packets=result['packets'],year_statistics=session.statistics,
    experimental=True,isolated=sys.flags.isolated,general_release_passed=False)))
'''
    process=subprocess.run([str(folder/'runtime/python.exe'),'-X','utf8','-B','-I','-c',probe],cwd=folder,
        env=environment,capture_output=True,text=True,encoding='utf-8',timeout=120)
    if process.returncode:raise RuntimeError('Relocated continuous mode failed:\n'+process.stdout+process.stderr)
    return json.loads(process.stdout)


if __name__=="__main__":main()
