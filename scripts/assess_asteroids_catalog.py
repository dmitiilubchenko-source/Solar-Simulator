"""Annual 354-body dynamics: unchanged parent, independent RK45 and JPL residuals."""
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from solar_simulator.perturbers import solar_system_asteroids_full,solar_system_asteroids_catalog
from solar_simulator.oblateness import sun_earth_moon_quadrupoles

if __package__:
    from .assess_pluto import reference,PLUTO_REFERENCE_SHA256
    from .assess_orientation import sample
    from .assess_relative_coordinates import independent_reference,relative_states,REFERENCE_SHA256
    from .assess_solar_j2 import planetary_errors,PLANET_REFERENCE_SHA256
    from .assess_oblateness import pair_errors
    from .assess_resolved_moon import errors,states
    from .fetch_asteroid_catalog import inputs,year_blocks,decode_year,heliocentric_state,rotation,INITIAL_SHA,YEAR_MANIFEST_SHA
    from .independent_eih_rust import load_oracle
    from .independent_figure_vector import acceleration as reference_figures
else:
    from assess_pluto import reference,PLUTO_REFERENCE_SHA256
    from assess_orientation import sample
    from assess_relative_coordinates import independent_reference,relative_states,REFERENCE_SHA256
    from assess_solar_j2 import planetary_errors,PLANET_REFERENCE_SHA256
    from assess_oblateness import pair_errors
    from assess_resolved_moon import errors,states
    from fetch_asteroid_catalog import inputs,year_blocks,decode_year,heliocentric_state,rotation,INITIAL_SHA,YEAR_MANIFEST_SHA
    from independent_eih_rust import load_oracle
    from independent_figure_vector import acceleration as reference_figures

OPTIONS=dict(backend='rust',relative_pair=('Earth','Moon'),rtol=3e-14,position_atol=1e-5,velocity_atol=1e-11)


def comparison(a,b,initial):
    return dict(all_bodies=errors(a,b),
        moon_relative_to_earth=errors(relative_states(a,initial),relative_states(b,initial)))


def asteroid_residual(actual,initial,times,planets):
    """JPL future vectors are read only here, after free orbit integration."""
    catalog,manifest,segments,constants=inputs()
    identities={r['id'] for r in catalog['bodies'] if r['group']=='asteroid'}
    records=decode_year(manifest,year_blocks(manifest),segments,identities)
    names=[b.name for b in initial]
    transform=rotation()
    epochs=planets['epochs_jd_tdb']
    indices=[int(np.flatnonzero(times==(jd-epochs[0])*86400)[0]) for jd in epochs]
    sun=next(b for b in planets['bodies'] if b['name']=='Sun')
    result={}
    for row in catalog['bodies']:
        if row['group']!='asteroid': continue
        expected=np.array([(heliocentric_state(records[row['id']],jd).reshape(2,3)@transform.T).ravel()
            +np.array(s['position']+s['velocity']) for jd,s in zip(epochs,sun['states'])])
        result[row['name']]=errors(actual[indices,names.index(row['name'])],expected)
    if len(result)!=343: raise ValueError('Incomplete asteroid residual catalogue')
    return result


def main():
    pair=reference('docs/solar-system-moon-reference.json',REFERENCE_SHA256)
    planets=reference('docs/solar-system-reference.json',PLANET_REFERENCE_SHA256)
    pluto=reference('docs/pluto-reference.json',PLUTO_REFERENCE_SHA256)
    base,parent=solar_system_asteroids_full();initial,origin=solar_system_asteroids_catalog()
    if (len(initial)!=354 or not np.array_equal(states(base),states(initial[:27]))
            or [(b.name,b.mass,b.radius) for b in base]!=[(b.name,b.mass,b.radius) for b in initial[:27]]):
        raise ValueError('Catalog changes original bodies')
    times=(np.array(pair['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    if len(times)!=45 or times[0]!=0 or times[-1]!=31557600 or np.any(np.diff(times)<=0):
        raise ValueError('Wrong pinned annual grid')
    expected=np.stack([np.array([s['position']+s['velocity'] for s in b['states']]) for b in pair['bodies']],axis=1)
    expected_pluto=np.array([s['position']+s['velocity'] for s in pluto['bodies'][0]['states']])
    variants,values={},{}
    for name,bodies,data_origin,adjust in (
            ('sixteen_asteroids',base,parent,{}),('all_343',initial,origin,{}),
            ('all_343_tighter',initial,origin,dict(position_atol=1e-6,velocity_atol=1e-12))):
        start=time.perf_counter()
        actual,diagnostics=sample(bodies,data_origin,times,sun_earth_moon_quadrupoles(bodies,data_origin),
            **dict(OPTIONS,**adjust))
        values[name]=actual
        variants[name]=dict(pair=pair_errors(actual,expected,bodies,times),
            planets=planetary_errors(actual,bodies,times,planets),pluto_system=errors(actual[:,10],expected_pluto),
            elapsed_seconds=time.perf_counter()-start,**diagnostics)
        print(name,variants[name]['elapsed_seconds'],variants[name]['pair'],flush=True)
    Path('.tools').mkdir(exist_ok=True)
    np.savez_compressed('.tools/asteroids-catalog-production.npz',times=times,**values)
    oracle=load_oracle()
    independent,convergence=independent_reference(initial,sun_earth_moon_quadrupoles(initial,origin),times,
        levels=((1e-13,1800.),(3e-14,900.)),cache_name='asteroids-catalog-reference',
        acceleration_function=oracle,figure_acceleration_function=reference_figures)
    agreement=comparison(values['all_343'],independent,initial)
    tighter_agreement=comparison(values['all_343_tighter'],independent,initial)
    sensitivity=comparison(values['all_343'],values['all_343_tighter'],initial)
    passed=(agreement['all_bodies']['maximum_position_metres']<1
        and agreement['moon_relative_to_earth']['maximum_position_metres']<.1
        and sensitivity['all_bodies']['maximum_position_metres']<1
        and sensitivity['moon_relative_to_earth']['maximum_position_metres']<.1
        and tighter_agreement['all_bodies']['maximum_position_metres']<1
        and tighter_agreement['moon_relative_to_earth']['maximum_position_metres']<.1
        and variants['all_343']['maximum_relative_energy_budget_residual']<1e-10)
    variants['all_343']['asteroids']=asteroid_residual(values['all_343'],initial,times,planets)
    increment=comparison(values['all_343'][:,:27],values['sixteen_asteroids'],base)
    source_files=('scripts/independent_figure_vector.py','scripts/validation/eih_scalar.rs',
        'scripts/assess_relative_coordinates.py','scripts/assess_asteroids_catalog.py')
    doc=dict(physics='354 interacting bodies: Sun, planets, Moon, Pluto-System, all 343 asteroids; EIH 1PN + Sun J2 + prescribed Earth/Moon J2/C22',
        epoch_jd_tdb=origin.epoch_jd_tdb,duration_seconds=float(times[-1]),samples=len(times),
        dataset_sha256=origin.dataset_sha256,gm_sha256=origin.gm_sha256,base_dataset_sha256=parent.dataset_sha256,
        source_initial_catalogue_sha256=INITIAL_SHA,source_ranges_sha256=YEAR_MANIFEST_SHA,
        options=OPTIONS,variants=variants,added_327_asteroids_increment=increment,
        increment_by_original_body={b.name:errors(values['all_343'][:,i],values['sixteen_asteroids'][:,i]) for i,b in enumerate(base)},
        numerical_agreement=agreement,tighter_numerical_agreement=tighter_agreement,tolerance_sensitivity=sensitivity,
        independent_reference_convergence=convergence,checks_passed=passed,
        reference_sha256=dict(pair=REFERENCE_SHA256,planets=PLANET_REFERENCE_SHA256,pluto=PLUTO_REFERENCE_SHA256),
        independent_source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in source_files},
        limitations=['All 343 DE441 asteroids, not every asteroid in nature.',
            'No 30 KBOs or 44-AU ring, coupled spin/tides, higher multipoles or higher PN.',
            'Initial state only; future JPL vectors serve exclusively as validation.',
            'Sampled agreement, not a continuous/global error guarantee.'])
    Path('docs/asteroids-catalog-validation.json').write_text(json.dumps(doc,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    np.savez_compressed('.tools/asteroids-catalog-states.npz',times=times,reference=independent,**values)
    print('checks_passed',passed,'agreement',agreement,flush=True)
    if not passed: raise RuntimeError('Full catalogue annual numerical agreement failed')


if __name__=='__main__':
    main()
