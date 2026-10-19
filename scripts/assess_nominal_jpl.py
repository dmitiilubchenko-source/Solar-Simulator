"""Reproduce all 440 nominal DE441 comparisons without network or propagation."""
import argparse
from dataclasses import asdict
import hashlib
from io import BytesIO
import json
from pathlib import Path
from time import perf_counter
from zipfile import ZipFile

import numpy as np

from scripts.assess_dense_jpl import residuals
from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.assess_nominal_solar_packets import shared_epochs
from scripts.assess_sandbox_planets import states
from scripts.fixed_j2_year import inputs, verify, canonical
from scripts.newton_year import ROOT, NAMES, hashes
from scripts.nominal_jpl import PROTOCOL, parse_vectors, request_url, vectors
from solar_simulator.ephemerides import RESOLVED_IDS

ARCHIVE = 'docs/nominal-jpl440-inputs.zip'
ARCHIVE_SHA256 = '89b1d13600055ccb254515ebe9bdbc71ade0551d133ccee2a69947590f5cc4db'
NOMINAL_REPORT = 'docs/nominal-solar-packet20-validation.json'
NOMINAL_REPORT_SHA256 = '16c619a971484d05105326c481c76f014d4aefba8d9aa84fa3e9c5a79ec3bf77'
SOURCE_SNAPSHOT = 'docs/runtime-sources-before301.zip'
SOURCE_SNAPSHOT_SHA256 = 'a810441919c0ea429e43f66242f3d41ad58e4b0ba462bcaefab89b7630248e99'


def verify_frozen_sources(bindings):
    """Verify executed historical bytes, never qualify the current runtime.

    The pinned trajectory includes old UI/CLI sources. Their later development
    does not change that trajectory. Only exact archived bytes can satisfy an
    old source binding; input and installed-dependency checks remain separate.
    """
    archived = None
    for name, expected in bindings.items():
        normalized = name.replace('\\', '/')
        path = (ROOT/normalized).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            raise ValueError('Receipt path outside project: '+name)
        if path.is_file() and digest(path.read_bytes()) == expected:
            continue
        if archived is None:
            raw = (ROOT/SOURCE_SNAPSHOT).read_bytes()
            if digest(raw) != SOURCE_SNAPSHOT_SHA256:
                raise ValueError('Historical source archive SHA mismatch')
            with ZipFile(BytesIO(raw)) as snapshot:
                archived = {entry: snapshot.read(entry) for entry in snapshot.namelist()}
        if normalized not in archived or digest(archived[normalized]) != expected:
            raise ValueError('Frozen source SHA mismatch: '+name)
MODES = ('legacy_python', 'legacy_rust', 'continuous_rust')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_archive(path):
    raw = Path(path).read_bytes()
    if digest(raw) != ARCHIVE_SHA256:
        raise ValueError('Frozen 440-epoch archive SHA changed')
    with ZipFile(BytesIO(raw)) as archive:
        names = archive.namelist()
        expected = {'reference230.json', 'probe229.json', 'annual.json', 'annual.npz'}
        for body_id in RESOLVED_IDS:
            for kind in ('regular', 'final'):
                base = f'raw/horizons-{body_id}-{kind}'
                expected.update((base+'.json', base+'.request.json'))
        for body_id in (1, 399, 301):
            for kind in ('regular', 'jd'):
                base = f'probe/{body_id}-{kind}'
                expected.update((base+'.json', base+'.request.json'))
        if (len(names) != len(expected) or set(names) != expected
                or sum(info.file_size for info in archive.infolist()) > 20_000_000):
            raise ValueError('Unexpected archive file inventory/size')
        return {name: archive.read(name) for name in names}


def checked_response(files, file, record, body_id, times, kind):
    meta = json.loads(files[file.removesuffix('.json')+'.request.json'])
    if (meta != record or record['url'] != request_url(body_id, times, kind)
            or digest(files[file]) != record['sha256']):
        raise ValueError('Raw response SHA/request provenance mismatch')
    return parse_vectors(json.loads(files[file]), body_id, times)


def validate_probe(files):
    probe = json.loads(files['probe229.json'])
    if not probe['complete'] or not probe['checks_passed']:
        raise ValueError('Time probe did not qualify')
    verify(probe['source_sha256'])
    arrays, comparisons = {}, {}
    times = [0, 72000, 144000, 216000]
    index = 0
    for name, body_id in [('Mercury', 1), ('Earth', 399), ('Moon', 301)]:
        arrays[name] = {}
        for kind in ('regular', 'jd'):
            rows = checked_response(files, f'probe/{body_id}-{kind}.json',
                probe['requests'][index], body_id, times, kind)
            if rows != probe['rows'][name+'_'+kind]:
                raise ValueError('Published time probe rows changed')
            arrays[name][kind] = vectors(rows)
            index += 1
        difference = arrays[name]['regular']-arrays[name]['jd']
        comparisons[name] = dict(position_metres=float(np.linalg.norm(difference[:, :3], axis=1).max()),
            velocity_m_per_s=float(np.linalg.norm(difference[:, 3:], axis=1).max()))
    pair = (arrays['Moon']['regular']-arrays['Earth']['regular'])-(arrays['Moon']['jd']-arrays['Earth']['jd'])
    comparisons['Moon-Earth'] = dict(position_metres=float(np.linalg.norm(pair[:, :3], axis=1).max()),
        velocity_m_per_s=float(np.linalg.norm(pair[:, 3:], axis=1).max()))
    if (len(probe['requests']) != 6 or comparisons != probe['comparison']
            or any(row['position_metres'] >= (.2 if name == 'Moon-Earth' else 10.)
                or row['velocity_m_per_s'] >= (1e-4 if name == 'Moon-Earth' else .001)
                for name, row in comparisons.items())):
        raise ValueError('Time probe comparison failed')
    return comparisons


def validate_data(files, seed, prior_times):
    reference = json.loads(files['reference230.json'])
    times = epoch_grid()
    if (not reference['complete'] or not reference['checks_passed']
            or reference['protocol'] != PROTOCOL or reference['origin'] != asdict(seed.origin)
            or reference['units'] != 'SI' or reference['names'] != list(NAMES)
            or reference['ids'] != list(RESOLVED_IDS) or reference['epochs_seconds'] != times.tolist()
            or reference['initial_dataset_changed'] or reference['physical_parameters_fitted']
            or not reference['fetched_after_free_integration'] or not reference['requests_sequential']
            or [b['name'] for b in reference['bodies']] != list(NAMES)
            or [b['id'] for b in reference['bodies']] != list(RESOLVED_IDS)):
        raise ValueError('Reference model/time/lineage/body mismatch')
    verify(reference['source_sha256'])
    old = json.loads((ROOT/'docs/qualification-grid-reference.json').read_bytes())
    _, a, b = shared_epochs(times, prior_times)
    matrices = []
    for body, old_body in zip(reference['bodies'], old['bodies']):
        rows = []
        if len(body['requests']) != 2:
            raise ValueError('Require regular and final response per body')
        for request, kind, grid, suffix in zip(body['requests'], ('regular', 'jd'),
                (times[:-1], times[-1:]), ('regular', 'final')):
            file = f"raw/horizons-{body['id']}-{suffix}.json"
            if request['file'] != file or request['kind'] != kind or request['epochs_seconds'] != grid.tolist():
                raise ValueError('Request epoch/order mismatch')
            record = {key: value for key, value in request.items() if key not in ('file', 'kind', 'epochs_seconds')}
            rows.extend(checked_response(files, file, record, body['id'], grid, kind))
        if rows != body['states']:
            raise ValueError('Published reference differs from raw vectors')
        matrix = vectors(rows)
        old_matrix = vectors(old_body['states'])
        p = float(np.linalg.norm(matrix[a, :3]-old_matrix[b, :3], axis=1).max())
        v = float(np.linalg.norm(matrix[a, 3:]-old_matrix[b, 3:], axis=1).max())
        if (p >= .01 or v >= 1e-8 or p != body['overlap_position_metres']
                or v != body['overlap_velocity_m_per_s'] or not body['overlap_passed']):
            raise ValueError('Old 24-epoch overlap failed')
        matrices.append(matrix)
    expected = np.asarray(matrices).transpose(1, 0, 2)
    speed = float(np.linalg.norm(expected[:, :, 3:], axis=2).max())
    pair_speed = float(np.linalg.norm(expected[:, 4, 3:]-expected[:, 3, 3:], axis=1).max())
    if speed >= 100000. or pair_speed >= 2000.:
        raise ValueError('Predeclared time-displacement speed ceilings exceeded')
    return expected, dict(maximum_barycentric_speed_m_per_s=speed,
        maximum_moon_relative_speed_m_per_s=pair_speed,
        maximum_jd_offset_seconds=max(abs(r['jd_offset_seconds']) for body in reference['bodies'] for r in body['states']),
        maximum_calendar_offset_seconds=max(abs(r['calendar_offset_seconds']) for body in reference['bodies'] for r in body['states']),
        representation_envelope_seconds=.0001, body_allowance_metres=10., pair_allowance_metres=.2,
        exact_jpl_epoch_coincidence_claim=False)


def validate_frozen(files, seed, verify_dependencies=False):
    verify({NOMINAL_REPORT: NOMINAL_REPORT_SHA256})
    published = json.loads((ROOT/NOMINAL_REPORT).read_bytes())
    receipt = json.loads(files['annual.json'])
    pins = {Path(name).name: sha for name, sha in published['receipts'].items()}
    if (digest(files['annual.json']) != pins['annual.json']
            or digest(files['annual.npz']) != pins['annual.npz']
            or digest(files['annual.npz']) != receipt['npz_sha256']
            or receipt != published['measurements'] or not receipt['complete']
            or not receipt['checks_passed'] or not receipt['reference_passed']
            or receipt['names'] != list(NAMES) or receipt['origin'] != asdict(seed.origin)
            or receipt['settings'] != canonical(asdict(seed.settings))
            or receipt['masses_kg'] != [body.mass for body in seed.bodies]
            or not receipt['initial_experiment_preserved']):
        raise ValueError('Frozen nominal trajectory qualification/lineage mismatch')
    verify_frozen_sources(receipt['source_sha256'])
    verify(receipt['input_sha256'])
    if verify_dependencies and hashes(receipt['dependency_sha256']) != receipt['dependency_sha256']:
        raise ValueError('Actual nominal calculation dependency changed')
    with np.load(BytesIO(files['annual.npz']), allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    np.testing.assert_array_equal(arrays['times'], epoch_grid())
    np.testing.assert_array_equal(arrays['initial'], states(seed.bodies))
    for name in (*MODES, 'level_0', 'level_1', 'level_2'):
        value = arrays[name]
        if value.shape != (440, 10, 6) or not np.isfinite(value).all():
            raise ValueError('Invalid frozen trajectory shape/values')
        if name in MODES:
            np.testing.assert_array_equal(value[0].view(np.uint64), arrays['initial'].view(np.uint64))
    return arrays, receipt


def timed_residuals(actual, expected, times):
    epochs = [2461321.5+float(t)/86400 for t in times]
    row = residuals(actual, expected, list(NAMES), epochs)
    for index, name in enumerate(NAMES):
        delta = np.linalg.norm(actual[:, index, :3]-expected[:, index, :3], axis=1)
        metric = row['jpl_residuals'][name]
        metric.update(position_rms_metres=float(np.sqrt(np.mean(delta**2))),
            final_position_metres=float(delta[-1]), worst_nominal_seconds=float(times[np.argmax(delta)]),
            position_plus_timing_allowance_metres=metric['position_metres']+10.,
            timing_aware_goal_passed=bool(metric['position_metres']+10. < 10000.))
    delta = np.linalg.norm((actual[:, 4, :3]-actual[:, 3, :3])-(expected[:, 4, :3]-expected[:, 3, :3]), axis=1)
    metric = row['moon_relative_jpl']
    metric.update(position_rms_metres=float(np.sqrt(np.mean(delta**2))), final_position_metres=float(delta[-1]),
        worst_nominal_seconds=float(times[np.argmax(delta)]),
        position_plus_timing_allowance_metres=metric['position_metres']+.2,
        timing_aware_goal_passed=bool(metric['position_metres']+.2 < 1000.))
    row['timing_aware_goals_passed'] = bool(row['physical_goals_passed'] and metric['timing_aware_goal_passed']
        and all(r['timing_aware_goal_passed'] for r in row['jpl_residuals'].values()))
    return row


def qualified(numerical_passed, candidates, reference):
    return bool(numerical_passed and set(candidates) == set(MODES)
        and all(r['timing_aware_goals_passed'] for r in candidates.values())
        and reference['timing_aware_goals_passed'])


def run(archive, output, verify_dependencies=False):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'.tools'):
        raise ValueError('Preserve previous evidence; use fresh project .tools output')
    output.parent.mkdir(parents=True, exist_ok=True)
    start = perf_counter()
    sources = hashes([PROTOCOL, 'scripts/assess_nominal_jpl.py', 'scripts/nominal_jpl.py'])
    report = dict(complete=False, checks_passed=False, protocol=PROTOCOL, source_sha256=sources,
        archive_sha256=ARCHIVE_SHA256, archive_bytes=Path(archive).stat().st_size,
        network_used=False, integration_performed=False, runtime_modified=False,
        physical_parameters_fitted=False, general_release=False,
        full_year_noether_balances_verified=False, original_noether_visibility_failure_preserved=True,
        current_dependencies_reverified=verify_dependencies, no_new_physical_precision_claim=True)
    try:
        files = load_archive(archive)
        seed, prior_times, *_ = inputs()
        arrays, receipt = validate_frozen(files, seed, verify_dependencies)
        probe = validate_probe(files)
        expected, timing = validate_data(files, seed, prior_times)
        candidates = {name: timed_residuals(arrays[name], expected, epoch_grid()) for name in MODES}
        reference = timed_residuals(arrays['level_2'], expected, epoch_grid())
        report.update(complete=True, checks_passed=qualified(receipt['checks_passed'], candidates, reference),
            origin=asdict(seed.origin), settings=receipt['settings'], units='SI', names=list(NAMES),
            epochs_seconds=epoch_grid().tolist(), time_probe=probe, timing=timing,
            candidates=candidates, independent_reference=reference,
            previous_24_epoch_results={n: dict(moon_relative_jpl=receipt['candidates'][n]['moon_relative_jpl']) for n in MODES},
            reference_refinement=receipt['reference_comparisons']['1_to_2'],
            archive_files_sha256={name: digest(raw) for name, raw in files.items()})
        if hashes(sources) != sources:
            raise ValueError('Source changed during offline audit')
    except BaseException as error:
        report.update(complete=False, checks_passed=False, failure=dict(type=type(error).__name__, message=str(error)))
        raise
    finally:
        report['wall_seconds'] = perf_counter()-start
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print('offline JPL440 complete, passed', report['checks_passed'], 'seconds', report['wall_seconds'], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=Path(ARCHIVE))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-local-dependencies', action='store_true')
    args = parser.parse_args()
    if not run(args.archive, args.output, args.verify_local_dependencies)['checks_passed']:
        raise RuntimeError('JPL440 goals failed; full evidence retained')


if __name__ == '__main__':
    main()
