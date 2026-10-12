"""Measure the added Pluto-system source on the unchanged one-year benchmark."""
import hashlib
import json
from pathlib import Path

import numpy as np
from solar_simulator.ephemerides import solar_system
from solar_simulator.perturbers import solar_system_pluto,PLUTO_DATASET_SHA256,PLUTO_GM_SHA256
from solar_simulator.oblateness import sun_earth_moon_quadrupoles,SOLAR_PROFILE_SHA256
from solar_simulator.orientation import PROFILE_SHA256
from solar_simulator.simulation import G
if __package__:
    from .assess_orientation import sample
    from .assess_relative_coordinates import independent_reference,relative_states,REFERENCE_SHA256
    from .assess_solar_j2 import planetary_errors,PLANET_REFERENCE_SHA256,BENCHMARK_OPTIONS
    from .assess_oblateness import pair_errors
    from .assess_resolved_moon import errors,states
    from .assess_relativity import YEAR
else:
    from assess_orientation import sample
    from assess_relative_coordinates import independent_reference,relative_states,REFERENCE_SHA256
    from assess_solar_j2 import planetary_errors,PLANET_REFERENCE_SHA256,BENCHMARK_OPTIONS
    from assess_oblateness import pair_errors
    from assess_resolved_moon import errors,states
    from assess_relativity import YEAR

PLUTO_REFERENCE_SHA256 = "4d353cc1dc1fe934ccdeed86252f9f1959a1469471edb00d95d841f710ecb1a8"


def reference(path,sha):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=sha:
        raise ValueError('Pinned validation reference changed')
    return json.loads(raw)


def initial_screening(initial):
    """Constant initial-acceleration scale, not an orbit or a global bound."""
    source=initial[-1]
    acceleration=[]
    for body in initial[:-1]:
        r=source.position.subtract(body.position)
        d=r.magnitude()
        acceleration.append(np.array([r.x,r.y,r.z])*(G*source.mass/d**3))
    return dict(meaning='0.5 * |initial direct Pluto acceleration| * year^2; not a global bound or propagated orbit',
        absolute_metres={body.name:float(np.linalg.norm(a)*YEAR**2/2) for body,a in zip(initial[:-1],acceleration)},
        earth_relative_to_sun_metres=float(np.linalg.norm(acceleration[3]-acceleration[0])*YEAR**2/2),
        moon_relative_to_earth_metres=float(np.linalg.norm(acceleration[4]-acceleration[3])*YEAR**2/2))


def main():
    pair=reference('docs/solar-system-moon-reference.json',REFERENCE_SHA256)
    planets=reference('docs/solar-system-reference.json',PLANET_REFERENCE_SHA256)
    pluto=reference('docs/pluto-reference.json',PLUTO_REFERENCE_SHA256)
    base,base_origin=solar_system(resolved_moon=True)
    initial,origin=solar_system_pluto()
    if (not np.array_equal(states(initial[:-1]),states(base))
            or [(b.name,b.mass,b.radius) for b in initial[:-1]]!=[(b.name,b.mass,b.radius) for b in base]
            or pair['dataset_sha256']!=base_origin.dataset_sha256 or pluto['dataset_sha256']!=origin.dataset_sha256):
        raise ValueError('Initial dataset or reference lineage mismatch')
    times=(np.array(pair['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    expected=np.stack([np.array([s['position']+s['velocity'] for s in b['states']]) for b in pair['bodies']],axis=1)
    expected_pluto=np.array([s['position']+s['velocity'] for s in pluto['bodies'][0]['states']])
    if pluto['epochs_jd_tdb']!=pair['epochs_jd_tdb'] or times[-1]!=YEAR:
        raise ValueError('Validation epochs mismatch')
    variants={}
    values={}
    for name,bodies,data_origin,options in (
            ('without_pluto',base,base_origin,{}),('with_pluto',initial,origin,{}),
            ('with_pluto_tighter',initial,origin,dict(rtol=3e-14,position_atol=1e-6,velocity_atol=1e-12)),
            ('with_pluto_recommended',initial,origin,dict(rtol=3e-14))):
        actual,diagnostics=sample(bodies,data_origin,times,sun_earth_moon_quadrupoles(bodies,data_origin),
            **dict(dict(relative_pair=('Earth','Moon'),position_atol=1e-5,velocity_atol=1e-11),**options))
        values[name]=actual
        variants[name]=dict(pair=pair_errors(actual,expected,bodies,times),
            planets=planetary_errors(actual,bodies,times,planets),**diagnostics)
        if name!='without_pluto':
            variants[name]['pluto_system']=errors(actual[:,-1],expected_pluto)
        print(name,variants[name]['pair'],flush=True)
    Path('.tools').mkdir(exist_ok=True)
    np.savez_compressed('.tools/pluto-production-states.npz',times=times,**values)
    def differences(a,b):
        return dict(all_bodies=errors(a,b),moon_relative_to_earth=errors(relative_states(a,initial),relative_states(b,initial)))
    screening=initial_screening(initial)
    print('Initial Pluto acceleration scale',screening,flush=True)
    independent,convergence=independent_reference(initial,sun_earth_moon_quadrupoles(initial,origin),times,
        levels=((1e-13,1800.),(3e-14,900.)),cache_name='pluto-reference-progress')
    agreement=differences(values['with_pluto'],independent)
    recommended_agreement=differences(values['with_pluto_recommended'],independent)
    passed=all(d['all_bodies']['maximum_position_metres']<1
        and d['moon_relative_to_earth']['maximum_position_metres']<.1 for d in (agreement,recommended_agreement))
    report=dict(physics='EIH 1PN + solar J2 + prescribed Earth/Moon J2/C22 + Pluto system barycentre',
        epoch_jd_tdb=origin.epoch_jd_tdb,duration_seconds=YEAR,samples=len(times),options=BENCHMARK_OPTIONS,
        dataset_sha256=PLUTO_DATASET_SHA256,gm_sha256=PLUTO_GM_SHA256,base_dataset_sha256=base_origin.dataset_sha256,
        solar_profile_sha256=SOLAR_PROFILE_SHA256,orientation_profile_sha256=PROFILE_SHA256,
        pair_reference_sha256=REFERENCE_SHA256,planet_reference_sha256=PLANET_REFERENCE_SHA256,
        pluto_reference_sha256=PLUTO_REFERENCE_SHA256,variants=variants,
        added_pluto_increment=differences(values['with_pluto'][:,:-1],values['without_pluto']),
        added_pluto_increment_by_body={b.name:errors(values['with_pluto'][:,i],values['without_pluto'][:,i]) for i,b in enumerate(base)},
        tolerance_sensitivity=differences(values['with_pluto'],values['with_pluto_tighter']),
        initial_acceleration_screening=screening,independent_reference_convergence=convergence,
        numerical_agreement=agreement,recommended_numerical_agreement=recommended_agreement,
        recommended_options=dict(relative_pair=['Earth','Moon'],rtol=3e-14,position_atol_metres=1e-5,velocity_atol_m_per_s=1e-11),
        checks_passed=passed,
        limitation='Pluto system barycentre only, no resolved Pluto satellites, asteroids or KBO population/ring. Full reaction and EIH on all 11 bodies; fixed solar pole, prescribed Moon orientation. Sampled agreement/local tolerances do not bound global errors. No fitted future states used in runtime.')
    Path('docs/pluto-validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    np.savez_compressed('.tools/pluto-states.npz',times=times,reference=independent,**values)
    print('checks_passed',passed,'agreement',agreement,flush=True)
    if not passed:
        raise RuntimeError('Pluto independent numerical agreement failed')


if __name__=='__main__':
    main()
