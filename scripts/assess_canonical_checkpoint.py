"""Checkpoint file restart with explicit reuse of pinned independent trajectories."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts.canonical_checkpoint import (CanonicalCheckpoint, CORE_SOURCES, canonical_text,
    to_document, from_document, save, load, velocity_export, verify_sources, evolve)
from scripts.canonical_initial import SIUnits
from scripts.rigid_pn_model import Parameters, invariants
from scripts.nbody_pn_spin import Parameters as PointParameters
from scripts.assess_rigid_pn import attitudes, convert_reference, compare
from solar_simulator.rotation import RigidFigure


def bits_equal(first, second):
    return np.array_equal(np.array(first, dtype=float).view(np.uint64),
                          np.array(second, dtype=float).view(np.uint64))


def audit():
    output = ROOT/'docs/canonical-checkpoint-validation.json'
    if output.exists(): raise FileExistsError('Preserve canonical checkpoint audit')
    policy = json.loads((ROOT/'scripts/canonical-checkpoint-policy.json').read_text(encoding='utf-8'))
    sha = lambda p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    parent = json.loads((ROOT/'docs/rigid-pn-validation.json').read_text(encoding='utf-8'))
    for name, expected in parent['code_sha256'].items():
        if sha(name) != expected: raise ValueError(f'Changed parent source: {name}')
    archive_path = '.tools/rotation57/rigid-pn-trajectories.npz'
    if sha(archive_path) != parent['trajectory_archive_sha256']:
        raise ValueError('Changed independent trajectory archive')
    data = np.load(ROOT/archive_path, allow_pickle=False)
    initial = np.array(parent['initial_state']); original = parent['policy']
    params = Parameters(PointParameters(tuple(original['masses']), original['c']),
        RigidFigure(original['masses'][original['figure_index']], tuple(original['moments']),
                    original['bounding_radius']), original['figure_index'])
    times = np.linspace(0., policy['periods']*policy['nominal_period'], policy['samples'])
    if (not np.array_equal(data['production-state'][0], initial)
            or not np.array_equal(times, data['reference-0-times'])
            or not np.array_equal(times, data['reference-1-times'])
            or original['periods'] != policy['periods']):
        raise ValueError('Different initial state/reference grids or duration')
    count = len(params.orbital.masses); scales = np.linalg.norm(initial[:-4].reshape(3, count, 3), axis=-1)
    if not np.array_equal(scales, np.array(parent['scales_x_p_S_per_body'])):
        raise ValueError('Different parent comparison scales')
    component_scales = np.r_[np.repeat(scales.ravel(), 3), np.ones(4)]
    source_paths = list(CORE_SOURCES)+['scripts/assess_canonical_checkpoint.py',
        'scripts/canonical-checkpoint-policy.json', 'tests/test_canonical_checkpoint.py',
        'docs/rigid-pn-validation.json', archive_path, 'scripts/assess_rigid_pn.py',
        'scripts/independent_rigid_pn.py', 'scripts/independent_nbody_pn_spin.py']
    hashes = {p: sha(p) for p in source_paths}
    source_records = [dict(path=p, sha256=h) for p, h in hashes.items()]
    control = dict(method='canonical-per-block-DOP853', rtol=policy['production_rtol'],
        atol=(policy['production_rtol']*policy['production_atol_over_rtol']*component_scales).tolist(),
        max_step=policy['max_step_over_period']*policy['nominal_period'])
    metadata = dict(frame=dict(name=original['initial_frame'], centre='canonical-ADM-centres',
        spin_basis='finite-H-spatial-Euclidean', time_coordinate='model-coordinate-time',
        epoch_jd=None, evolution='fixed-no-reboost'), units=dict(kind='synthetic-G1'), integration=control,
        provenance=dict(interpretation='synthetic finite-H initial state from immutable change 57',
                        physical_mapping_certified=False, sources=source_records))
    start = CanonicalCheckpoint(params, tuple(initial), tuple(initial), 0., canonical_text(metadata))
    work = ROOT/'.tools/rotation59'; work.mkdir(exist_ok=True)
    save(work/'initial.json', start); loaded = load(work/'initial.json'); verify_sources(loaded, ROOT)
    print('worst-block canonical trajectory', flush=True); timer = time.perf_counter()
    end, full = evolve(loaded, times, source_root=ROOT)
    full_seconds = time.perf_counter()-timer
    split = policy['split_sample']; timer = time.perf_counter()
    middle, first = evolve(start, times[:split+1], source_root=ROOT)
    save(work/'middle.json', middle); continued = load(work/'middle.json')
    final, last = evolve(continued, times[split:], source_root=ROOT)
    joined = np.vstack([first[:-1], last]); restart_seconds = time.perf_counter()-timer
    references = [convert_reference(data[f'reference-{i}-state'], count, params.index) for i in range(2)]
    rotations = attitudes(full)
    difference = compare(full[:, :-4], rotations, *references[-1], scales)
    uncertainty = compare(*references[0], *references[1], scales)
    restart = compare(full[:, :-4], rotations, joined[:, :-4], attitudes(joined), scales)
    values = [invariants(y, params) for y in full]
    h = np.array([v[0] for v in values]); p = np.array([v[1] for v in values]); j = np.array([v[2] for v in values])
    point = [i for i in range(count) if i != params.index]
    norms = np.linalg.norm(full[:, :-4].reshape(-1, 3, count, 3)[:, 2, point], axis=-1)
    metrics = dict(energy_relative=float(np.max(abs(h-h[0]))/abs(h[0])),
        momentum_scaled=float(np.linalg.norm(p-p[0], axis=1).max()/scales[1].sum()),
        angular_momentum_relative=float(np.linalg.norm(j-j[0], axis=1).max()/np.linalg.norm(j[0])),
        point_spin_norm_relative=float(np.max(abs(norms-norms[0])/norms[0])),
        quaternion_norm=float(np.max(abs(np.linalg.norm(full[:, -4:], axis=1)-1))),
        reference_difference=difference['maximum'], reference_uncertainty=uncertainty['maximum'],
        restart_difference=restart['maximum'])
    confirmations = dict(synthetic_roundtrip_bitwise=bits_equal(middle.state, continued.state)
        and bits_equal(middle.initial, continued.initial) and bits_equal(start.state, loaded.state),
        metadata_preserved=(start.metadata_json == loaded.metadata_json == continued.metadata_json == final.metadata_json),
        loaded_sources_verified=True)
    for name, doc in [('legacy_rejected',dict(schema=10, bodies=[], rotations=[])),
                      ('velocity_export_rejected',velocity_export(continued))]:
        try: from_document(doc)
        except ValueError: confirmations[name] = True
        else: confirmations[name] = False
    lunar_parent = json.loads((ROOT/'docs/canonical-initial-validation.json').read_text(encoding='utf-8'))
    for name, expected in lunar_parent['code_sha256'].items():
        if sha(name) != expected: raise ValueError(f'Changed initial-data audit source: {name}')
    moon = lunar_parent['lunar_diagnostic']; profile_path = 'src/solar_simulator/data/lunar-spin-solid-equivalent-20261008.json'
    profile = json.loads((ROOT/profile_path).read_text(encoding='utf-8'))
    units = SIUnits(**moon['units']); dataset = json.loads((ROOT/'src/solar_simulator/data/solar-system-moon-20261008.json').read_text(encoding='utf-8'))
    masses = tuple(b['gm_m3_s2']/units.gravitational_constant/units.mass_kg for b in dataset['bodies'])
    a = moon['body_names'].index('Moon')
    lunar_params = Parameters(PointParameters(masses, lunar_parent['policy']['lunar_diagnostic']['c_m_s']/units.velocity_m_s),
        RigidFigure(masses[a], tuple(np.array(profile['moments_kg_m2'])/units.inertia_kg_m2), profile['exclusion_radius_m']/units.length_m), a)
    lunar_state = tuple(moon['state_for_model_diagnostic']); lunar_meta = json.loads(canonical_text(metadata))
    lunar_meta['units'] = dict(kind='SI-similarity', **moon['units'])
    lunar_meta['frame'].update(name=moon['frame']+'; conditional SSB canonical boundary',
                              time_coordinate='TDB-as-input-coordinate-time', epoch_jd=moon['epoch_jd_tdb'])
    lunar_meta['integration']['atol'] = [policy['lunar_zero_point_spin_atol']]*(len(lunar_state)-4)+[1e-13]*4
    lunar_meta['provenance']['interpretation'] = moon['interpretation']
    lunar_meta['provenance']['sources'] += [dict(path=p, sha256=h) for p,h in moon['input_sha256'].items()]
    lunar_meta['provenance']['sources'].append(dict(path='docs/canonical-initial-validation.json', sha256=sha('docs/canonical-initial-validation.json')))
    lunar = CanonicalCheckpoint(lunar_params, lunar_state, lunar_state, 0., canonical_text(lunar_meta))
    save(work/'conditional-lunar-initial.json', lunar); lunar_loaded = load(work/'conditional-lunar-initial.json')
    verify_sources(lunar_loaded, ROOT); exported = velocity_export(lunar_loaded)
    input_velocity = np.array([b['velocity'] for b in dataset['bodies']]); input_rate = np.array(moon['initial_attitude_rate_per_s'])
    metrics['lunar_export_velocity_relative'] = float(np.max(np.linalg.norm(np.array(exported['velocity_m_s'])-input_velocity, axis=1)/np.linalg.norm(input_velocity, axis=1)))
    metrics['lunar_export_rate_relative'] = float(np.linalg.norm(np.array(exported['attitude_rate_per_s'])-input_rate)/np.linalg.norm(input_rate))
    confirmations['lunar_roundtrip_bitwise'] = bits_equal(lunar_state, lunar_loaded.state) and lunar.metadata_json == lunar_loaded.metadata_json
    if hashes != {p: sha(p) for p in source_paths}: raise ValueError('Checkpoint audit sources changed')
    arrays_path = work/'checkpoint-trajectories.npz'
    with arrays_path.open('xb') as stream: np.savez_compressed(stream, times=times, production=full, restarted=joined)
    result = dict(change=59, policy=policy, metrics=metrics, confirmations=confirmations,
        reference_components=difference, reference_uncertainty_components=uncertainty, restart_components=restart,
        job_seconds=dict(production=full_seconds,restart=restart_seconds), code_sha256=hashes,
        parent_reference_archive_sha256=parent['trajectory_archive_sha256'],
        checkpoint_files={str(p.relative_to(ROOT).as_posix()):sha(p.relative_to(ROOT)) for p in work.glob('*.json') if p.name!='before.json'},
        trajectory_archive_local_path=arrays_path.relative_to(ROOT).as_posix(), trajectory_archive_sha256=sha(arrays_path.relative_to(ROOT)),
        physical_lunar_mapping_certified=False, legacy_migrated=False, runtime_changed=False,
        passed=all(metrics[k]<limit for k,limit in policy['criteria'].items()) and all(confirmations[k] for k in policy['required_true']))
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(metrics=metrics, confirmations=confirmations, passed=result['passed']),indent=2),flush=True)
    return result['passed']


if __name__ == '__main__':
    sys.exit(0 if audit() else 1)
