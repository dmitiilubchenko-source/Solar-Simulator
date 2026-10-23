"""Offline verification of profile359 without C/native, RK45 solves or local caches."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import numpy as np

from scripts.assess_ias15_native_newton import cargo_hashes, same_array
from scripts.assess_native_newton_year import NATIVE_RECEIPT, OLD_KEYS, PROTOCOL
from scripts.assess_newton_year import candidate_metrics
from scripts.ias15_native_newton import MODES
from scripts.ias15_reference import EPSILONS
from scripts.ias15_restart import bits
from scripts.kepler_transport import ROOT, public_path, sha
from scripts.release_history import historical_sha, historical_cargo_hashes
from scripts.native_newton_year import force_metrics
from scripts.newton_year import NAMES, packet_end
from scripts.newton_year_cache import load

RECEIPT = 'docs/native-newton-year-validation.json'


def replay(root=ROOT):
    root = Path(root).resolve()
    seed, profiles, qualified, historical = load(root)
    report = json.loads((root/RECEIPT).read_text(encoding='utf-8'))
    previous = json.loads((root/NATIVE_RECEIPT).read_text(encoding='utf-8'))
    flags = ('complete', 'source_unchanged', 'input_unchanged', 'library_unchanged',
             'native_unchanged', 'cargo_unchanged', 'all_c_control175_bitexact')
    if (report.get('protocol') != PROTOCOL or report.get('solver') != 'IAS15 C/native Newton N-body research'
            or not all(report.get(k) is True for k in flags) or report['cache_qualification'] != qualified
            or report.get('runtime_modified') is not False or report.get('production_eligible') is not False
            or report['origin'] != asdict(seed.origin) or report['names'] != list(NAMES)
            or bits(report['masses_kg']) != bits([b.mass for b in seed.bodies])):
        raise ValueError('Require complete, qualified N-body research receipt')
    for name, expected in {**report['source_sha256'], **report['input_sha256']}.items():
        if historical_sha(root, name, expected) != expected:
            raise ValueError('Changed N-body source/input: '+name)
    if (report['cargo_hash_policy'] != 'cargo-crlf-to-lf-v1'
            or historical_cargo_hashes(root, report['cargo_lf_sha256']) != report['cargo_lf_sha256']
            or report['cargo_raw_before_sha256'] != report['cargo_raw_after_sha256']
            or set(report['cargo_raw_before_sha256']) != set(report['cargo_lf_sha256'])
            or any(len(bytes.fromhex(v)) != 32 for v in report['cargo_raw_before_sha256'].values())
            or any(report[k] != previous[k] for k in ('native', 'library_files_sha256', 'external_source_archive_sha256'))):
        raise ValueError('Changed N-body build/native provenance')
    path = public_path(root, report['sample_archive'])
    if sha(path) != report['npz_sha256']:
        raise ValueError('N-body archive SHA mismatch')
    with np.load(path, allow_pickle=False) as saved:
        data = {k:saved[k].copy() for k in saved.files}
    initial = profiles['year']['initial']
    measured_force = force_metrics(report['masses_kg'], initial[:, :3], report['initial_force']['actual'])
    if measured_force != report['initial_force'] or not measured_force['checks_passed']:
        raise ValueError('Independent N-body force metric differs')
    if set(report['results']) != set(profiles) or set(report['cost']) != set(profiles) or set(report['reference_recheck']) != set(profiles):
        raise ValueError('Pilot and year required')
    expected_keys, passed, packets, packet_states = set(), {}, 0, 0
    for profile, cached in profiles.items():
        name = profile+'__reference_recheck'
        expected_keys.add(name)
        row = report['reference_recheck'][profile]
        old_level = {k:v for k,v in historical[profile]['reference_levels'][2].items()
                     if k not in ('elapsed_seconds', 'initial_roundtrip')}
        if (not same_array(data[name], cached['reference_2']) or row['bitexact'] is not True
                or row['values_sha256'] != hashlib.sha256(bits(data[name])).hexdigest()
                or row['metadata'] != old_level or row['seconds'] <= 0
                or any(v['position_metres'] != 0. or v['velocity_m_per_s'] != 0. for v in row['differences'].values())):
            raise ValueError('Regenerated RK45 reference does not match historical cache')
        expected_variants = {str(e)+'__'+m for e in EPSILONS for m in MODES}
        if set(report['results'][profile]) != expected_variants or set(report['cost'][profile]) != expected_variants:
            raise ValueError('Both force modes and epsilon values required')
        clock, endpoints = 0., [0.]
        for epoch in cached['times']:
            while clock < epoch:
                clock = packet_end(clock, float(epoch), seed.settings.dt)
                endpoints.append(clock)
        passed[profile] = 0
        for epsilon in EPSILONS:
            for mode in MODES:
                key, prefix = str(epsilon)+'__'+mode, profile+'__'+str(epsilon)+'__'+mode+'__'
                expected_keys.update(prefix+k for k in ('values', 'packet_endpoints', 'packet_states'))
                values, ends, states = (data[prefix+k] for k in ('values', 'packet_endpoints', 'packet_states'))
                if (values.shape != cached['reference_2'].shape or states.shape != (len(endpoints), 10, 6)
                        or ends.shape != (len(endpoints),) or bits(ends) != bits(endpoints)
                        or bits(values[0]) != bits(initial) or bits(states[0]) != bits(initial)
                        or not np.isfinite(values).all() or not np.isfinite(states).all()):
                    raise ValueError('Invalid N-body IC/shape/clock')
                for epoch, value in zip(cached['times'], values):
                    indices = np.flatnonzero(ends == epoch)
                    if len(indices) != 1 or bits(states[indices[0]]) != bits(value):
                        raise ValueError('Output differs from its exact N-body packet state')
                row = report['results'][profile][key]
                metrics = candidate_metrics(values, cached['reference_2'], seed, True)
                if metrics != row['metrics']:
                    raise ValueError('N-body per-body/relative/invariant metrics differ')
                stats, cost = row['statistics'], report['cost'][profile][key]
                if (stats['packets'] != len(ends)-1 or stats['simulations'] != 1 or stats['steps_done'] <= 0
                        or stats['force_evaluations'] < stats['steps_done'] or stats['velocity_dependent'] is not False
                        or stats['gravity'] != ('basic' if mode == 'basic' else 'none')
                        or row['c_control175_bitexact'] is not (mode == 'basic')
                        or row['repeated_bitexact'] is not True or row['counter_bitexact'] is not True
                        or len(cost['seconds']) != 3 or min(cost['seconds']) <= 0
                        or sorted(cost['seconds'])[1] != cost['median_seconds']):
                    raise ValueError('N-body counter/model/timing metadata differs')
                if mode == 'basic':
                    old_stats = historical[profile]['candidates'][OLD_KEYS[epsilon]]['statistics']
                    if not same_array(values, cached[OLD_KEYS[epsilon]]) or any(stats[k] != old_stats[k]
                            for k in ('steps_done', 'packets', 'force_evaluations')):
                        raise ValueError('C control differs from175')
                passed[profile] += int(metrics['checks_passed'])
                packets += stats['packets']
                packet_states += len(ends)
    if set(data) != expected_keys or len(data) != 26 or report['all_checks_passed'] is not all(n == 4 for n in passed.values()):
        raise ValueError('N-body array set or aggregate gate differs')
    return dict(profiles=2, variants=8, passed=passed, arrays=26, packets=packets, packet_states=packet_states,
                cache_reference_reproduced=True, metrics_reproduced=True, runtime_modified=False,
                all_checks_passed=report['all_checks_passed'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    print(json.dumps(replay(parser.parse_args().root), indent=2))


if __name__ == '__main__':
    main()
