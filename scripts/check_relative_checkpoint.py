"""Repeat a year of pair integration through CLI, save/load and 45 intervals."""
import json
import argparse
from pathlib import Path
import subprocess
import sys
import numpy as np
from solar_simulator.storage import load
from solar_simulator.oblateness import potential_energy,PrescribedQuadrupole,SOLAR_PROFILE_SHA256
if __package__:
    from .assess_resolved_moon import states,errors
    from .assess_orientation import sample
else:
    from assess_resolved_moon import states,errors
    from assess_orientation import sample

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--figures',choices=['earth-moon-q2','sun-earth-moon-q2'],default='earth-moon-q2')
parser.add_argument('--preset',choices=['solar-system-moon','solar-system-pluto','solar-system-asteroids','solar-system-asteroids-full'],default='solar-system-moon')
parser.add_argument('--rtol',type=float,default=None)
parser.add_argument('--output')
args=parser.parse_args()
with_sun=args.figures=='sun-earth-moon-q2'
with_pluto=args.preset in ('solar-system-pluto','solar-system-asteroids','solar-system-asteroids-full')
with_asteroids=args.preset in ('solar-system-asteroids','solar-system-asteroids-full')
with_full=args.preset=='solar-system-asteroids-full'
rtol=args.rtol if args.rtol is not None else 3e-14 if with_pluto else 1e-13
folder=Path('.tools/asteroids-full-cli-year' if with_full else '.tools/asteroids-cli-year' if with_asteroids else '.tools/pluto-cli-year' if with_pluto else '.tools/solar-cli-year' if with_sun else '.tools/relative-cli-year'); folder.mkdir(exist_ok=True)
start,whole,half,resumed=[folder/f'{name}.json' for name in ('start','whole','half','resumed')]
for cli_args in (
    ['new',args.preset,str(start),'--physics','eih-1pn','--figures',args.figures,
     '--relative-pair','Earth','Moon','--rtol',str(rtol),'--position-atol','1e-5','--velocity-atol','1e-11'],
    ['run',str(start),str(whole),'--steps','8766'],
    ['run',str(start),str(half),'--steps','4383'],
    ['run',str(half),str(resumed),'--steps','4383']):
    result=subprocess.run([sys.executable,'-B','-m','solar_simulator',*cli_args],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
original,full,restart=map(load,(start,whole,resumed))
assert full.time==restart.time==31557600 and full.settings.relative_pair==('Earth','Moon')
a,b=states(full.bodies),states(restart.bodies)
all_difference=errors(a,b)
pair_difference=errors(a[4]-a[3],b[4]-b[3])
work_scale=abs(potential_energy(original.bodies,original.settings.figures))
work_difference=abs(full.orientation_work-restart.orientation_work)
assert all_difference['maximum_position_metres']<.1
assert pair_difference['maximum_position_metres']<.05
assert work_difference/work_scale<1e-7
report=dict(time_seconds=full.time,relative_pair=list(full.settings.relative_pair),
    whole_vs_half_restart_all_bodies=all_difference,whole_vs_half_restart_pair=pair_difference,
    orientation_work_difference_joules=work_difference,work_difference_over_initial_figure_energy=work_difference/work_scale)
doc=json.loads(Path('docs/solar-system-moon-reference.json').read_text())
times=(np.array(doc['epochs_jd_tdb'])-original.origin.epoch_jd_tdb)*86400
segmented,diagnostics=sample(original.bodies,original.origin,times,original.settings.figures,
    relative_pair=original.settings.relative_pair,rtol=original.settings.rtol,
    position_atol=original.settings.position_atol,velocity_atol=original.settings.velocity_atol)
comparison=dict(all_bodies=errors(a,segmented[-1]),
    moon_relative_to_earth=errors(a[4]-a[3],segmented[-1,4]-segmented[-1,3]))
assert comparison['all_bodies']['maximum_position_metres']<.1
assert comparison['moon_relative_to_earth']['maximum_position_metres']<.05
report['whole_vs_45_intervals']=comparison
report['work_difference_from_45_intervals_joules']=abs(full.orientation_work-diagnostics['final_orientation_work_joules'])
assert report['work_difference_from_45_intervals_joules']/work_scale<1e-7
daily_times=np.append(np.arange(366)*86400.,full.time)
daily,daily_diagnostics=sample(original.bodies,original.origin,daily_times,original.settings.figures,
    relative_pair=original.settings.relative_pair,rtol=original.settings.rtol,
    position_atol=original.settings.position_atol,velocity_atol=original.settings.velocity_atol)
daily_comparison=dict(all_bodies=errors(a,daily[-1]),
    moon_relative_to_earth=errors(a[4]-a[3],daily[-1,4]-daily[-1,3]))
assert daily_comparison['all_bodies']['maximum_position_metres']<.1
assert daily_comparison['moon_relative_to_earth']['maximum_position_metres']<.05
report['whole_vs_daily_intervals']=daily_comparison
report['work_difference_from_daily_intervals_joules']=abs(full.orientation_work-daily_diagnostics['final_orientation_work_joules'])
assert report['work_difference_from_daily_intervals_joules']/work_scale<1e-7
report['dataset_sha256']=original.origin.dataset_sha256
if with_pluto:
    report['gm_sha256']=original.origin.gm_sha256
report['profile_sha256']=next(f.profile_sha256 for f in original.settings.figures if isinstance(f,PrescribedQuadrupole))
if with_sun:
    report['solar_profile_sha256']=SOLAR_PROFILE_SHA256
report['rtol']=original.settings.rtol
report['position_atol_metres']=original.settings.position_atol
report['velocity_atol_m_per_s']=original.settings.velocity_atol
report['checks_passed']=True
output=Path(args.output or ('docs/asteroids-full-checkpoint-validation.json' if with_full else 'docs/asteroids-checkpoint-validation.json' if with_asteroids else 'docs/pluto-checkpoint-validation.json' if with_pluto else 'docs/solar-checkpoint-validation.json' if with_sun else 'docs/relative-checkpoint-validation.json'))
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
