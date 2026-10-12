"""Fresh annual 384-body integration, two-level independent RK45 and KBO effect.

The parent and expanded model use identical tolerances, epoch and original
states. JPL future vectors are used only for assessment after propagation.
No fit, source-driven acceleration, ring or mass selection is performed.
"""
import hashlib
import json
from pathlib import Path
import time
import numpy as np

from solar_simulator.perturbers import solar_system_asteroids_catalog,solar_system_kuiper
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from scripts.assess_orientation import sample
from scripts.assess_pluto import reference,PLUTO_REFERENCE_SHA256
from scripts.assess_relative_coordinates import independent_reference,REFERENCE_SHA256
from scripts.assess_solar_j2 import planetary_errors,PLANET_REFERENCE_SHA256
from scripts.assess_oblateness import pair_errors
from scripts.assess_resolved_moon import errors,states
from scripts.assess_asteroids_catalog import comparison
from scripts.assess_asteroid_catalog import individual_acceleration,differential_acceleration,summed
from scripts.fetch_kuiper_data import inputs,year_blocks,decode_year,heliocentric_state,rotation,YEAR_MANIFEST_SHA,PACKED_SHA
from scripts.build_kuiper_dataset import INITIAL_SHA
from scripts.independent_eih_rust import load_oracle
from scripts.independent_figure_vector import acceleration as reference_figures

OPTIONS=dict(backend='rust',relative_pair=('Earth','Moon'),error_control='per-body',
    rtol=3e-14,position_atol=1e-7,velocity_atol=1e-13)


def force_screen(rows,records,constants,planets,pair):
    """Stable direct/tidal Newtonian diagnostic at 13 fixed source snapshots."""
    transform=rotation();scale=(constants['AU']*1000)**3/86400**2
    mu=np.array([constants[r['constant']]*scale for r in rows])
    targets={b['name']:b for b in planets['bodies']}
    moon={b['name']:b for b in pair['bodies']}
    values={name:[] for name in targets if name not in ('Earth-Moon',)}
    values.update({'Earth':[],'Moon':[],'Moon-minus-Earth':[],'Earth-minus-Sun':[]})
    for index,jd in enumerate(planets['epochs_jd_tdb']):
        k=pair['epochs_jd_tdb'].index(jd)
        sun=np.array(targets['Sun']['states'][index]['position'])
        positions={name:np.array(body['states'][index]['position'])-sun for name,body in targets.items()}
        positions.update({name:np.array(moon[name]['states'][k]['position'])-sun for name in ('Earth','Moon')})
        sources=np.array([heliocentric_state(records[r['id']],jd)[:3]@transform.T for r in rows])
        for name in values:
            if name=='Moon-minus-Earth':
                a=differential_acceleration(sources,mu,positions['Earth'],positions['Moon']-positions['Earth'])
            elif name=='Earth-minus-Sun':
                a=differential_acceleration(sources,mu,np.zeros(3),positions['Earth'])
            else:
                a=individual_acceleration(sources,mu,positions[name])
            values[name].append(summed(a))
    return dict(samples=len(planets['epochs_jd_tdb']),mass_count=30,
        gm_m3_s2=float(np.sum(mu)),targets={name:dict(initial_vector_m_per_s2=v[0].tolist(),
            maximum_magnitude_m_per_s2=float(np.linalg.norm(v,axis=1).max())) for name,v in values.items()},
        limitation='Newtonian force diagnostic on 13 JPL snapshots; not a continuous maximum or an orbit error bound. Full propagation includes the existing EIH and quadrupoles.')


def source_residual(actual,initial,times,planets,rows,records):
    """Free KBO orbit against later original SB441 states, assessed after solving."""
    names=[b.name for b in initial];transform=rotation()
    epochs=planets['epochs_jd_tdb']
    indices=[int(np.flatnonzero(times==(jd-epochs[0])*86400)[0]) for jd in epochs]
    sun=next(b for b in planets['bodies'] if b['name']=='Sun')
    result={}
    for row in rows:
        expected=np.array([(heliocentric_state(records[row['id']],jd).reshape(2,3)@transform.T).ravel()
            +np.array(s['position']+s['velocity']) for jd,s in zip(epochs,sun['states'])])
        result[row['name']]=errors(actual[indices,names.index(row['name'])],expected)
    return result


def main():
    base,parent=solar_system_asteroids_catalog();initial,origin=solar_system_kuiper()
    if (len(initial)!=384 or not np.array_equal(states(base),states(initial[:354]))
            or [(b.name,b.mass,b.radius,b.spin.x,b.spin.y,b.spin.z) for b in base]
                !=[(b.name,b.mass,b.radius,b.spin.x,b.spin.y,b.spin.z) for b in initial[:354]]):
        raise ValueError('KBO model altered parent states or masses')
    pair=reference('docs/solar-system-moon-reference.json',REFERENCE_SHA256)
    times=(np.array(pair['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    if len(times)!=45 or times[0]!=0 or times[-1]!=31557600 or np.any(np.diff(times)<=0):
        raise ValueError('Invalid pinned annual grid')
    arrays={};runs={}
    choices=(('parent_354',base,parent,{}),('kuiper_384',initial,origin,{}),
        ('kuiper_384_tighter',initial,origin,dict(position_atol=1e-8,velocity_atol=1e-14)))
    for name,bodies,data_origin,adjustment in choices:
        start=time.perf_counter()
        actual,diagnostics=sample(bodies,data_origin,times,sun_earth_moon_quadrupoles(bodies,data_origin),
            **dict(OPTIONS,**adjustment))
        arrays[name]=actual
        runs[name]=dict(elapsed_seconds=time.perf_counter()-start,options=dict(OPTIONS,**adjustment),**diagnostics)
        np.savez_compressed('.tools/kuiper-production.npz',times=times,**arrays)
        print(name,runs[name],flush=True)
    oracle=load_oracle()
    independent,convergence=independent_reference(initial,sun_earth_moon_quadrupoles(initial,origin),times,
        levels=((1e-13,1800.),(3e-14,900.)),cache_name='kuiper-reference',
        acceleration_function=oracle,figure_acceleration_function=reference_figures)
    # Future external positions enter diagnostics only after every free run.
    planets=reference('docs/solar-system-reference.json',PLANET_REFERENCE_SHA256)
    pluto=reference('docs/pluto-reference.json',PLUTO_REFERENCE_SHA256)
    expected=np.stack([np.array([s['position']+s['velocity'] for s in b['states']]) for b in pair['bodies']],axis=1)
    expected_pluto=np.array([s['position']+s['velocity'] for s in pluto['bodies'][0]['states']])
    for name,bodies,_,_ in choices:
        runs[name].update(pair=pair_errors(arrays[name],expected,bodies,times),
            planets=planetary_errors(arrays[name],bodies,times,planets),
            pluto_system=errors(arrays[name][:,10],expected_pluto))
    rows,manifest,segments,constants=inputs()
    records=decode_year(manifest,year_blocks(manifest),segments,{r['id'] for r in rows})
    runs['kuiper_384']['kuiper_bodies']=source_residual(arrays['kuiper_384'],initial,times,planets,rows,records)
    agreement=comparison(arrays['kuiper_384'],independent,initial)
    tighter=comparison(arrays['kuiper_384_tighter'],independent,initial)
    sensitivity=comparison(arrays['kuiper_384'],arrays['kuiper_384_tighter'],initial)
    increment=comparison(arrays['kuiper_384'][:,:354],arrays['parent_354'],base)
    # Bounds are numerical checks, fixed before examining the annual result.
    checks={name:(row['all_bodies']['maximum_position_metres']<.1
        and row['moon_relative_to_earth']['maximum_position_metres']<.02)
        for name,row in (('agreement',agreement),('tighter_agreement',tighter),
            ('tolerance_sensitivity',sensitivity),('reference_convergence',convergence))}
    checks['energy_budget']=all(run['maximum_relative_energy_budget_residual']<1e-10 for run in runs.values())
    passed=all(checks.values())
    code=('scripts/assess_kuiper.py','scripts/assess_relative_coordinates.py',
        'scripts/independent_figure_vector.py','scripts/validation/eih_scalar.rs',
        'src/solar_simulator/perturbers.py','src/solar_simulator/accuracy.py',
        'src/solar_simulator/error_control.py','src/solar_simulator/native_forces.py',
        'rust/solar_core/src/relativity.rs')
    report=dict(schema=1,body_count=len(initial),added_kuiper_bodies=30,
        epoch_jd_tdb=origin.epoch_jd_tdb,duration_seconds=float(times[-1]),samples=len(times),
        dataset_sha256=origin.dataset_sha256,gm_sha256=origin.gm_sha256,base_dataset_sha256=parent.dataset_sha256,
        source_initial_sha256=INITIAL_SHA,source_manifest_sha256=YEAR_MANIFEST_SHA,packed_source_sha256=PACKED_SHA,
        physics='384 interacting point masses; Rust EIH 1PN; prescribed Sun/Earth/Moon quadrupoles; relative Earth-Moon; per-body DOP853. No Kuiper ring.',
        variants=runs,numerical_agreement=agreement,tighter_numerical_agreement=tighter,
        tolerance_sensitivity=sensitivity,independent_reference_convergence=convergence,
        added_kuiper_increment=increment,increment_by_parent_body={b.name:errors(arrays['kuiper_384'][:,i],
            arrays['parent_354'][:,i]) for i,b in enumerate(base)},
        force_screen=force_screen(rows,records,constants,planets,pair),checks=checks,checks_passed=passed,
        reference_sha256=dict(pair=REFERENCE_SHA256,planets=PLANET_REFERENCE_SHA256,pluto=PLUTO_REFERENCE_SHA256),
        code_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in code},
        limitations=['45 sample epochs, not a continuous/global error bound.',
            'Source interpolation validation is distinct from numerical integration and physical truth.',
            'Independent reference has its own convergence uncertainty; no reuse of the 354-body reference.',
            'All 30 KBO masses, not all bodies in nature; KBO satellites unresolved.',
            'No 36-point Kuiper ring, autonomous spin/tides, higher multipoles or higher PN.',
            'Future JPL states do not tune parameters or drive the simulator.'])
    Path('docs/kuiper-validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    np.savez_compressed('.tools/kuiper-states.npz',times=times,reference=independent,**arrays)
    print('checks_passed',passed,'checks',checks,'increment',increment,'agreement',agreement,flush=True)
    if not passed:
        raise RuntimeError('384-body annual numerical verification failed; all results retained')


if __name__=='__main__':
    main()
