"""Numerically verify 144-point refinement; preserve the failed 36-point audit."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from solar_simulator.kuiper_ring import solar_system_ring
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from scripts.assess_kuiper_ring import (grid,metadata,write,checked_cache,digest,CODE)
from scripts.assess_kuiper import OPTIONS
from scripts.assess_orientation import sample
from scripts.independent_anchored_reference import independent_reference
from scripts.independent_eih_rust import load_oracle
from scripts.independent_figure_vector import acceleration as reference_figures
from scripts.assess_asteroids_catalog import comparison


def run(part):
    initial,origin=solar_system_ring(144,0);_,_,_,times=grid()
    start=time.perf_counter()
    if part=='reference':
        _,convergence=independent_reference(initial,sun_earth_moon_quadrupoles(initial,origin),times,
            levels=((1e-13,1800.),(3e-14,900.)),cache_name='ring-refined-independent',
            acceleration_function=load_oracle(),figure_acceleration_function=reference_figures)
        extra=dict(convergence=convergence)
    else:
        options=dict(OPTIONS,position_atol=1e-8,velocity_atol=1e-14)
        value,diagnostics=sample(initial,origin,times,sun_earth_moon_quadrupoles(initial,origin),**options)
        np.savez_compressed('.tools/ring-refined-tighter.npz',times=times,tighter=value)
        extra=dict(options=options,diagnostics=diagnostics)
    archive=f'.tools/ring-refined-{ "independent" if part=="reference" else "tighter"}.npz'
    result=metadata(archive,dataset_sha256=origin.dataset_sha256,body_count=len(initial),
        elapsed_seconds=time.perf_counter()-start,**extra)
    result['code_sha256'].update({p:digest(p) for p in
        ('scripts/assess_ring_resolution.py','scripts/kuiper-ring-refinement-policy.json')})
    write(archive.replace('.npz','-meta.json'),result)
    print('refined',part,'finished',result['elapsed_seconds'],'s',flush=True)


def assemble():
    initial,origin=solar_system_ring(144,0);_,_,_,times=grid()
    arrays,production_meta=checked_cache('ring-production',times)
    levels,oracle_meta=checked_cache('ring-refined-independent',times)
    tighter,tighter_meta=checked_cache('ring-refined-tighter',times)
    original=json.loads(Path('docs/kuiper-ring-validation.json').read_text(encoding='utf-8'))
    policy=json.loads(Path('scripts/kuiper-ring-refinement-policy.json').read_text(encoding='utf-8'))
    if original['geometry_criterion_passed'] or original['checks_passed']:
        raise ValueError('Refinement must retain the real failing original audit')
    for meta in (oracle_meta,tighter_meta):
        if meta['dataset_sha256']!=origin.dataset_sha256 or meta['body_count']!=528:
            raise ValueError('Wrong refined orbit lineage')
    numerical=dict(agreement=comparison(arrays['ring_144_0'],levels['level_1'],initial),
        tighter_agreement=comparison(tighter['tighter'],levels['level_1'],initial),
        tolerance_sensitivity=comparison(arrays['ring_144_0'],tighter['tighter'],initial),
        reference_convergence=comparison(levels['level_0'],levels['level_1'],initial))
    if numerical['reference_convergence']!=oracle_meta['convergence']:
        raise ValueError('Changed refined convergence')
    geometry={name:original['geometry_comparisons'][name] for name in policy['geometry_comparisons']}
    checks={name:row['all_bodies']['maximum_position_metres']<policy['numerical_all_bodies_metres']
        and row['moon_relative_to_earth']['maximum_position_metres']<policy['numerical_relative_moon_metres']
        for name,row in numerical.items()}
    checks['geometry']=all(row['major_systems']['maximum_position_metres']<policy['geometry_major_systems_metres']
        and row['moon_relative_to_earth']['maximum_position_metres']<policy['geometry_relative_moon_metres'] for row in geometry.values())
    checks['energy']=all(value['maximum_relative_energy_budget_residual']<policy['relative_energy_budget']
        for value in (production_meta['runs']['ring_144_0'],tighter_meta['diagnostics']))
    code=dict(production_meta['code_sha256']);code.update(oracle_meta['code_sha256'])
    result=dict(schema=1,model='own fully interacting ring: 144-point resolution refinement',
        body_count=528,dataset_sha256=origin.dataset_sha256,gm_sha256=origin.gm_sha256,
        policy_sha256=digest('scripts/kuiper-ring-refinement-policy.json'),policy=policy,
        epoch_jd_tdb=origin.epoch_jd_tdb,duration_seconds=float(times[-1]),samples=len(times),
        original_audit_sha256=digest('docs/kuiper-ring-validation.json'),original_audit_passed=False,
        numerical_checks=numerical,geometry_comparisons=geometry,checks=checks,checks_passed=all(checks.values()),
        recommended_options=OPTIONS,variant=original['variants']['ring_144_0'],
        tighter_diagnostics=tighter_meta['diagnostics'],independent_elapsed_seconds=oracle_meta['elapsed_seconds'],
        production_archive_sha256=production_meta['archive_sha256'],reference_archive_sha256=oracle_meta['archive_sha256'],
        tighter_archive_sha256=tighter_meta['archive_sha256'],code_sha256=code,
        limitations=original['limitations']+['Failed 36-point geometry criterion preserved; model phase/counts changed for convergence, not fitted to future JPL states.'])
    write('docs/kuiper-ring-refinement-validation.json',result)
    print('Refined checks',checks,'agreement',numerical['agreement'],flush=True)
    if not result['checks_passed']:raise RuntimeError('Refined annual criteria failed; result preserved')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part',choices=('reference','tighter','report'),required=True)
    args=parser.parse_args()
    if args.part=='report':assemble()
    else:run(args.part)


if __name__=='__main__':main()
