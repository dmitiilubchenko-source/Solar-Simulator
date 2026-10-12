"""Same one-year benchmark: three or sixteen live asteroid masses with an unchanged parent."""
import argparse
import json
from pathlib import Path
import numpy as np
from solar_simulator.perturbers import solar_system_pluto,solar_system_asteroids,solar_system_asteroids_full
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
if __package__:
    from .assess_pluto import reference,PLUTO_REFERENCE_SHA256
    from .assess_orientation import sample
    from .assess_relative_coordinates import independent_reference,relative_states,REFERENCE_SHA256
    from .assess_solar_j2 import planetary_errors,PLANET_REFERENCE_SHA256
    from .assess_oblateness import pair_errors
    from .assess_resolved_moon import errors,states
    from .assess_relativity import YEAR
else:
    from assess_pluto import reference,PLUTO_REFERENCE_SHA256
    from assess_orientation import sample
    from assess_relative_coordinates import independent_reference,relative_states,REFERENCE_SHA256
    from assess_solar_j2 import planetary_errors,PLANET_REFERENCE_SHA256
    from assess_oblateness import pair_errors
    from assess_resolved_moon import errors,states
    from assess_relativity import YEAR

REFERENCE_SHA='eb8c0f3db89c5945e5a597ba59f0ccf40513696a97acf2722873af22fe66b6ff'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full',action='store_true');parser.add_argument('--rust-reference',action='store_true')
    args=parser.parse_args()
    prefix='asteroids-full' if args.full else 'asteroids'
    reference_sha='e74e59990cec890803095972c3141fde7c1caa289b8118b7613867f811e6ce2a' if args.full else REFERENCE_SHA
    base_key,full_key,tight_key=('three_asteroids','sixteen_asteroids','sixteen_asteroids_tighter') if args.full else ('without_asteroids','with_asteroids','with_asteroids_tighter')
    pair=reference('docs/solar-system-moon-reference.json',REFERENCE_SHA256)
    planets=reference('docs/solar-system-reference.json',PLANET_REFERENCE_SHA256)
    pluto=reference('docs/pluto-reference.json',PLUTO_REFERENCE_SHA256)
    asteroids=reference('docs/'+prefix+'-reference.json',reference_sha)
    base,base_origin=(solar_system_asteroids if args.full else solar_system_pluto)();initial,origin=(solar_system_asteroids_full if args.full else solar_system_asteroids)()
    base_count=len(base)
    if (not np.array_equal(states(initial[:base_count]),states(base))
            or [(b.name,b.mass,b.radius) for b in initial[:base_count]]!=[(b.name,b.mass,b.radius) for b in base]
            or asteroids['dataset_sha256']!=origin.dataset_sha256
            or asteroids['base_dataset_sha256']!=base_origin.dataset_sha256
            or asteroids['epochs_jd_tdb']!=pair['epochs_jd_tdb']):
        raise ValueError('Initial data/reference lineage mismatch')
    times=(np.array(pair['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    expected=np.stack([np.array([s['position']+s['velocity'] for s in b['states']]) for b in pair['bodies']],axis=1)
    expected_pluto=np.array([s['position']+s['velocity'] for s in pluto['bodies'][0]['states']])
    options=dict(relative_pair=('Earth','Moon'),rtol=3e-14,position_atol=1e-5,velocity_atol=1e-11)
    variants={};values={}
    for name,bodies,data_origin,adjust in (
            (base_key,base,base_origin,{}),(full_key,initial,origin,{}),
            (tight_key,initial,origin,dict(position_atol=1e-6,velocity_atol=1e-12))):
        actual,diagnostics=sample(bodies,data_origin,times,sun_earth_moon_quadrupoles(bodies,data_origin),**dict(options,**adjust))
        values[name]=actual
        variants[name]=dict(pair=pair_errors(actual,expected,bodies,times),
            planets=planetary_errors(actual,bodies,times,planets),pluto_system=errors(actual[:,10],expected_pluto),**diagnostics)
        if name!=base_key:
            variants[name]['asteroids']={b['name']:errors(actual[:,11+i],
                np.array([s['position']+s['velocity'] for s in b['states']])) for i,b in enumerate(asteroids['bodies'])}
        print(name,variants[name]['pair'],flush=True)
    np.savez_compressed('.tools/'+prefix+'-production-states.npz',times=times,**values)
    oracle=None
    if args.rust_reference:
        if __package__: from .independent_eih_rust import load_oracle
        else: from independent_eih_rust import load_oracle
        oracle=load_oracle()
    independent,convergence=independent_reference(initial,sun_earth_moon_quadrupoles(initial,origin),times,
        levels=((1e-13,1800.),(3e-14,900.)),cache_name=prefix+'-reference-progress',acceleration_function=oracle)
    def difference(a,b):
        return dict(all_bodies=errors(a,b),moon_relative_to_earth=errors(relative_states(a,initial),relative_states(b,initial)))
    agreement=difference(values[full_key],independent)
    passed=agreement['all_bodies']['maximum_position_metres']<1 and agreement['moon_relative_to_earth']['maximum_position_metres']<.1
    report=dict(physics=f'{len(initial)} interacting point masses: EIH 1PN + Sun J2 + prescribed Earth/Moon J2/C22',
        epoch_jd_tdb=origin.epoch_jd_tdb,duration_seconds=YEAR,samples=len(times),dataset_sha256=origin.dataset_sha256,
        base_dataset_sha256=base_origin.dataset_sha256,gm_sha256=origin.gm_sha256,
        reference_sha256=reference_sha,options=options,variants=variants,
        added_asteroids_increment=difference(values[full_key][:,:base_count],values[base_key]),
        added_asteroids_increment_by_body={b.name:errors(values[full_key][:,i],values[base_key][:,i]) for i,b in enumerate(base)},
        tolerance_sensitivity=difference(values[full_key],values[tight_key]),
        independent_reference_convergence=convergence,numerical_agreement=agreement,checks_passed=passed,
        limitation=('All 16 SB441 asteroids; not the entire asteroid belt.' if args.full else 'Only Ceres, Pallas and Vesta, not the entire asteroid belt.')+' All bodies have full mass reaction and EIH. SB441 and DE441 future states serve only validation. Local tolerances and sampled numerical agreement are not a global error bound. Prescribed orientations, no coupled tides/spin or asteroid multipoles.')
    if oracle is not None:
        report['independent_scalar_force']=dict(language='Rust, developer oracle only',source_sha256=oracle.source_sha256,compiler=oracle.compiler_version,python_scalar_crosscheck='tests/test_independent_eih_rust.py')
    Path('docs/'+prefix+'-validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    np.savez_compressed('.tools/'+prefix+'-states.npz',times=times,reference=independent,**values)
    print('checks_passed',passed,'agreement',agreement,flush=True)
    if not passed: raise RuntimeError('Asteroid numerical agreement failed')


if __name__=='__main__':
    main()
