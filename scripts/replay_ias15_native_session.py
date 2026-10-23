"""Verify newly regenerated session results using the byte-identical public357 archive."""
import argparse
import json
from pathlib import Path

from scripts.assess_ias15_native_newton import cargo_hashes
from scripts.assess_ias15_native_session import PROTOCOL
from scripts.assess_ias15_restart import load_cases
from scripts.ias15_native_newton import MODES
from scripts.ias15_reference import EPSILONS
from scripts.kepler_transport import ROOT, public_path, sha
from scripts.release_history import historical_sha, historical_cargo_hashes
from scripts.replay_ias15_native_newton import RECEIPT as BASELINE, replay as replay357
from scripts.replay_ias15_session import replay as replay356

RECEIPT = 'docs/ias15-native-session-validation.json'


def replay(root=ROOT):
    root = Path(root).resolve()
    integrity = dict(coupling357=replay357(root), owned356=replay356(root))
    report = json.loads((root/RECEIPT).read_text(encoding='utf-8'))
    old = json.loads((root/BASELINE).read_text(encoding='utf-8'))
    flags = ('complete', 'source_unchanged', 'input_unchanged', 'library_unchanged',
             'native_unchanged', 'cargo_unchanged', 'all_baseline357_bitexact', 'archive_reused357')
    if (report.get('protocol') != PROTOCOL or report.get('solver') != 'IAS15 shared owned native research session'
            or not all(report.get(k) is True for k in flags) or report['baseline_integrity'] != integrity
            or report.get('runtime_modified') is not False or report.get('production_eligible') is not False):
        raise ValueError('Require complete native-session research receipt')
    for name, expected in {**report['source_sha256'], **report['input_sha256']}.items():
        if historical_sha(root, name, expected) != expected:
            raise ValueError('Changed live native-session source/input: '+name)
    if (report['sample_archive'] != old['sample_archive'] or report['npz_sha256'] != old['npz_sha256']
            or sha(public_path(root, report['sample_archive'])) != report['npz_sha256']
            or report['cargo_hash_policy'] != 'cargo-crlf-to-lf-v1'
            or historical_cargo_hashes(root, report['cargo_lf_sha256']) != report['cargo_lf_sha256']
            or report['cargo_lf_sha256'] != old['cargo_lf_sha256']
            or report['cargo_raw_before_sha256'] != report['cargo_raw_after_sha256']
            or set(report['cargo_raw_before_sha256']) != set(report['cargo_lf_sha256'])
            or any(len(bytes.fromhex(v)) != 32 for v in report['cargo_raw_before_sha256'].values())
            or any(report[k] != old[k] for k in ('native', 'library_files_sha256', 'external_source_archive_sha256'))):
        raise ValueError('Native-session array reuse or pinned input provenance differs')
    cases, _ = load_cases(root)
    if set(report['results']) != set(cases):
        raise ValueError('All nine session cases required')
    passed, packets, checkpoints = dict.fromkeys(MODES, 0), 0, 0
    for name in cases:
        if set(report['results'][name]) != {str(e)+'__'+m for e in EPSILONS for m in MODES}:
            raise ValueError('Both modes and epsilon values required')
        for epsilon in EPSILONS:
            for mode in MODES:
                key = str(epsilon)+'__'+mode
                row, baseline = report['results'][name][key], old['results'][name][key]
                stats = row['statistics']
                if (row['metrics'] != baseline['metrics'] or any(stats[k] != baseline['statistics'][k]
                        for k in ('packets', 'steps_done', 'force_evaluations', 'simulations'))
                        or stats['simulations'] != 1 or stats['attempts'] != stats['packets']
                        or stats['failed'] or not stats['closed'] or not stats['finished']
                        or stats['attempted_force_evaluations'] != stats['force_evaluations']
                        or not all(row[k] is True for k in ('baseline357_bitexact', 'repeated_bitexact', 'forcecounter_bitexact'))
                        or len(row['seconds']) != 3 or min(row['seconds']) <= 0
                        or sorted(row['seconds'])[1] != row['median_seconds']):
                    raise ValueError('Native-session metrics, lifecycle, counters or timing metadata differ')
                passed[mode] += int(row['metrics']['checks_passed'])
                packets += stats['packets']
                checkpoints += stats['packets']+1
    if report['all_checks_passed'] is not all(n == 18 for n in passed.values()):
        raise ValueError('Native-session aggregate gate differs')
    return dict(cases=9, variants=36, passed=passed, arrays=180, packets=packets,
        physical_checkpoints=checkpoints, all_baseline357_bitexact=True, archive_reused357=True,
        metrics_reproduced=True, all_checks_passed=report['all_checks_passed'], runtime_modified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    print(json.dumps(replay(parser.parse_args().root), indent=2))


if __name__ == '__main__':
    main()
