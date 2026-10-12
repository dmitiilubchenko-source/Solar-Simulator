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
    output=subprocess.check_output([str(runtime/"python.exe"),"-B","-I","-c",probe],cwd=folder,text=True,env=environment)
    result=json.loads(output)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print(f"RELOCATED_DIR={folder}")


if __name__=="__main__":
    main()
