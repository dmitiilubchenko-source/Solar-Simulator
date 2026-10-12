"""Free annual ring experiments with separate production/reference jobs.

The policy fixes mass, radius, six geometries and numerical criteria before
solving. Later JPL vectors enter assessment only. No phase is chosen by residual.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import quad_vec

from solar_simulator.kuiper_ring import solar_system_ring,MANIFEST_SHA256
from solar_simulator.perturbers import solar_system_kuiper
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from scripts.build_kuiper_ring import parameters,POLICY_SHA256
from scripts.assess_orientation import sample
from scripts.assess_kuiper import OPTIONS
from scripts.assess_asteroids_catalog import comparison
from scripts.assess_resolved_moon import errors,states
from scripts.assess_oblateness import pair_errors
from scripts.assess_solar_j2 import planetary_errors,PLANET_REFERENCE_SHA256
from scripts.assess_relative_coordinates import REFERENCE_SHA256,relative_states
from scripts.assess_pluto import reference,PLUTO_REFERENCE_SHA256
from scripts.independent_anchored_reference import independent_reference
from scripts.independent_eih_rust import load_oracle
from scripts.independent_figure_vector import acceleration as reference_figures
from scripts.assess_asteroid_catalog import differential_acceleration,summed

ROOT=Path(__file__).resolve().parents[1]
CODE=('scripts/assess_kuiper_ring.py','scripts/build_kuiper_ring.py',
    'scripts/independent_anchored_reference.py','scripts/independent_figure_vector.py',
    'scripts/validation/eih_scalar.rs','src/solar_simulator/kuiper_ring.py',
    'src/solar_simulator/perturbers.py','src/solar_simulator/experiment.py',
    'src/solar_simulator/accuracy.py','src/solar_simulator/error_control.py',
    'src/solar_simulator/native_forces.py','rust/solar_core/src/relativity.rs')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def grid():
    initial,origin=solar_system_ring()
    pair=reference('docs/solar-system-moon-reference.json',REFERENCE_SHA256)
    times=(np.array(pair['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    if len(times)!=45 or times[0]!=0 or times[-1]!=31557600 or np.any(np.diff(times)<=0):
        raise ValueError('Pinned annual grid required')
    return initial,origin,pair,times


def metadata(archive,**extra):
    return dict(schema=1,policy_sha256=POLICY_SHA256,manifest_sha256=MANIFEST_SHA256,
        archive_sha256=digest(archive),code_sha256={p:digest(p) for p in CODE},**extra)


def write(path,document):Path(path).write_text(json.dumps(document,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def production():
    _,_,pair,times=grid();arrays={};runs={}
    choices=[('no_ring',None,None)]+[(f'ring_{n}_{phase}',n,phase) for n in (36,72,144) for phase in (0,1)]
    choices.append(('ring_36_0_tighter',36,0))
    for name,n,phase in choices:
        bodies,origin=solar_system_kuiper() if n is None else solar_system_ring(n,phase)
        options=dict(OPTIONS)
        if name.endswith('tighter'):options.update(position_atol=1e-8,velocity_atol=1e-14)
        start=time.perf_counter()
        result,diagnostics=sample(bodies,origin,times,sun_earth_moon_quadrupoles(bodies,origin),**options)
        arrays[name]=result
        runs[name]=dict(body_count=len(bodies),dataset_sha256=origin.dataset_sha256,
            gm_sha256=origin.gm_sha256,points=n,phase_index=phase,options=options,
            elapsed_seconds=time.perf_counter()-start,**diagnostics)
        np.savez_compressed('.tools/ring-production.npz',times=times,**arrays)
        print(name,'finished',runs[name]['elapsed_seconds'],'s',flush=True)
    write('.tools/ring-production-meta.json',metadata('.tools/ring-production.npz',runs=runs))


def oracle():
    initial,origin,_,times=grid();start=time.perf_counter()
    _,convergence=independent_reference(initial,sun_earth_moon_quadrupoles(initial,origin),times,
        levels=((1e-13,1800.),(3e-14,900.)),cache_name='ring-independent',
        acceleration_function=load_oracle(),figure_acceleration_function=reference_figures)
    write('.tools/ring-independent-meta.json',metadata('.tools/ring-independent.npz',
        dataset_sha256=origin.dataset_sha256,body_count=len(initial),
        elapsed_seconds=time.perf_counter()-start,convergence=convergence,
        levels=[dict(rtol=1e-13,max_step_seconds=1800),dict(rtol=3e-14,max_step_seconds=900)]))


def checked_cache(name,times):
    meta=json.loads(Path(f'.tools/{name}-meta.json').read_text(encoding='utf-8'))
    path=Path(f'.tools/{name}.npz')
    if meta['policy_sha256']!=POLICY_SHA256 or meta['manifest_sha256']!=MANIFEST_SHA256 or meta['archive_sha256']!=digest(path):
        raise ValueError('Wrong ring experiment cache')
    for p,checksum in meta['code_sha256'].items():
        if digest(p)!=checksum:raise ValueError('Executed ring source changed: '+p)
    with np.load(path,allow_pickle=False) as archive:
        if not np.array_equal(archive['times'],times):raise ValueError('Wrong ring grid')
        arrays={key:archive[key].copy() for key in archive.files if key!='times'}
    if any(not np.all(np.isfinite(q)) for q in arrays.values()):raise ValueError('Nonfinite ring experiment')
    return arrays,meta


def field_diagnostic():
    au,gm=parameters();radius=44*au
    def continuous(p):
        def integrand(angle):
            d=radius*np.array([np.cos(angle),np.sin(angle),0.])-p
            return gm/(2*np.pi)*d/np.linalg.norm(d)**3
        return quad_vec(integrand,0,2*np.pi,epsabs=1e-28,epsrel=1e-13)[0]
    test_points={'centre':np.zeros(3),'Earth_radius':np.array([au,0.,0.]),
        'Neptune_radius':np.array([30*au,0.,0.]),'near_ring':np.array([.95*radius,0.,.12*radius]),
        'far_axis':np.array([0.,0.,3*radius])}
    result={}
    for name,p in test_points.items():
        expected=continuous(p);variants={}
        for n in (36,72,144):
            for phase in (0,1):
                bodies,_=solar_system_ring(n,phase);q=states(bodies)
                points=q[384:,:3]-q[0,:3];d=points-p
                actual=summed(gm/n*d/np.linalg.norm(d,axis=1)[:,None]**3)
                variants[f'{n}_{phase}']=dict(vector_m_per_s2=actual.tolist(),absolute_error_m_per_s2=float(np.linalg.norm(actual-expected)))
        result[name]=dict(position_metres=p.tolist(),continuous_vector_m_per_s2=expected.tolist(),variants=variants)
    bodies,_=solar_system_ring();q=states(bodies)
    moon=q[4,:3]-q[3,:3];earth=q[3,:3]-q[0,:3];points=q[384:,:3]-q[0,:3]
    tidal=summed(differential_acceleration(points,np.full(36,gm/36),earth,moon))
    independently=continuous(earth+moon)-continuous(earth)
    return dict(total_gm_m3_s2=gm,radius_metres=radius,points=result,
        moon_minus_earth_m_per_s2=tidal.tolist(),independent_quadrature_tidal_error_m_per_s2=float(np.linalg.norm(tidal-independently)),
        limitation='Initial field diagnostic; uniform continuous ring is a field comparator, not the autonomous self-gravitating model.')


def assemble():
    initial,origin,pair,times=grid()
    arrays,meta=checked_cache('ring-production',times);levels,oracle_meta=checked_cache('ring-independent',times)
    if set(levels)!={'level_0','level_1'} or oracle_meta['dataset_sha256']!=origin.dataset_sha256:
        raise ValueError('Independent ring oracle lineage mismatch')
    expected_names={'no_ring','ring_36_0_tighter'}|{f'ring_{n}_{p}' for n in (36,72,144) for p in (0,1)}
    if set(arrays)!=expected_names:raise ValueError('Incomplete six-geometry experiment')
    planets=reference('docs/solar-system-reference.json',PLANET_REFERENCE_SHA256)
    pluto=reference('docs/pluto-reference.json',PLUTO_REFERENCE_SHA256)
    expected=np.stack([np.array([s['position']+s['velocity'] for s in b['states']]) for b in pair['bodies']],axis=1)
    pluto_expected=np.array([s['position']+s['velocity'] for s in pluto['bodies'][0]['states']])
    runs=meta['runs']
    for name,q in arrays.items():
        n,p=runs[name]['points'],runs[name]['phase_index']
        bodies,data_origin=solar_system_kuiper() if n is None else solar_system_ring(n,p)
        if q.shape!=(45,len(bodies),6) or runs[name]['dataset_sha256']!=data_origin.dataset_sha256 or not np.array_equal(q[0],states(bodies)):
            raise ValueError('Ring initial states or shape changed')
        runs[name].update(pair=pair_errors(q,expected,bodies,times),
            planets=planetary_errors(q,bodies,times,planets),pluto_system=errors(q[:,10],pluto_expected))
    convergence=comparison(levels['level_0'],levels['level_1'],initial)
    if convergence!=oracle_meta['convergence']:raise ValueError('Oracle convergence changed')
    numerical=dict(agreement=comparison(arrays['ring_36_0'],levels['level_1'],initial),
        tighter_agreement=comparison(arrays['ring_36_0_tighter'],levels['level_1'],initial),
        tolerance_sensitivity=comparison(arrays['ring_36_0'],arrays['ring_36_0_tighter'],initial),
        reference_convergence=convergence)
    geometry={}
    parent,_=solar_system_kuiper()
    def geometry_comparison(a,b):
        return dict(major_systems=errors(a[:,:11],b[:,:11]),all_original_384=errors(a[:,:384],b[:,:384]),
            moon_relative_to_earth=errors(relative_states(a,initial),relative_states(b,initial)))
    for phase in (0,1):
        for n,m in ((36,72),(72,144)):
            geometry[f'{n}_vs_{m}_phase_{phase}']=geometry_comparison(arrays[f'ring_{n}_{phase}'],arrays[f'ring_{m}_{phase}'])
    for n in (36,72,144):geometry[f'phase_0_vs_1_{n}']=geometry_comparison(arrays[f'ring_{n}_0'],arrays[f'ring_{n}_1'])
    checks={name:row['all_bodies']['maximum_position_metres']<.1 and row['moon_relative_to_earth']['maximum_position_metres']<.02 for name,row in numerical.items()}
    checks['energy_budget']=all(r['maximum_relative_energy_budget_residual']<1e-10 for r in runs.values())
    geometry_passed=all(r['major_systems']['maximum_position_metres']<.1 and r['moon_relative_to_earth']['maximum_position_metres']<.02 for r in geometry.values())
    increment=comparison(arrays['ring_36_0'][:,:384],arrays['no_ring'],parent)
    report=dict(schema=1,model='own autonomous fully interacting discrete ring, not recovered DE441 initial states',
        body_count=len(initial),dataset_sha256=origin.dataset_sha256,gm_sha256=origin.gm_sha256,
        policy_sha256=POLICY_SHA256,manifest_sha256=MANIFEST_SHA256,epoch_jd_tdb=origin.epoch_jd_tdb,
        duration_seconds=float(times[-1]),samples=len(times),variants=runs,numerical_checks=numerical,
        geometry_comparisons=geometry,geometry_criterion_passed=geometry_passed,
        added_ring_increment=increment,increment_by_parent_body={b.name:errors(arrays['ring_36_0'][:,i],arrays['no_ring'][:,i]) for i,b in enumerate(parent)},
        independent_elapsed_seconds=oracle_meta['elapsed_seconds'],field_diagnostic=field_diagnostic(),
        numerical_checks_passed=all(checks.values()),checks=checks,checks_passed=all(checks.values()) and geometry_passed,
        criteria=dict(numerical_all_bodies_metres=.1,numerical_relative_moon_metres=.02,
            geometry_major_systems_metres=.1,geometry_relative_moon_metres=.02,relative_energy_budget=1e-10),
        production_archive_sha256=meta['archive_sha256'],independent_archive_sha256=oracle_meta['archive_sha256'],
        code_sha256=meta['code_sha256'],reference_sha256=dict(pair=REFERENCE_SHA256,planets=PLANET_REFERENCE_SHA256,pluto=PLUTO_REFERENCE_SHA256),
        limitations=['45 samples are not a continuous global error bound.',
            'Initial phases, circular velocities and ring-ring interactions are own explicit choices.',
            'Discrete point ring is not recovered DE441 or EPM2017 dynamics.',
            'All original KBO variations reported separately; no equivalence to a finite-width belt.',
            'Thin self-gravitating rings have singular continuum self-interactions; finite-count checks do not prove an infinite-point limit.',
            'No automatic geometry choice or fit to future JPL vectors.',
            'Prescribed lunar orientation remains conditional; no autonomous tides/spin.'])
    write('docs/kuiper-ring-validation.json',report)
    print('NUMERICAL',checks,'GEOMETRY',geometry_passed,'increment',increment,flush=True)
    if not report['checks_passed']:raise RuntimeError('Ring annual criteria failed; full result preserved')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part',choices=('all','production','reference','report'),default='all')
    args=parser.parse_args();Path('.tools').mkdir(exist_ok=True)
    if args.part in ('all','production'):production()
    if args.part in ('all','reference'):oracle()
    if args.part in ('all','report'):assemble()


if __name__=='__main__':main()
