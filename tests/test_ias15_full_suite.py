"""Independent evidence mutations; optional REBOUND is never imported."""
import base64
from copy import deepcopy
import json
from pathlib import Path
import struct

import numpy as np
import pytest

from scripts.assess_ias15_full_suite import CASES, run
from scripts.ias15_full_state import parse, pack, PREFIX
from scripts.replay_ias15_full_suite import validate_report, validate_pair, replay

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def complete_report():
    old = json.loads((ROOT/'docs/ias15-restart-validation.json').read_bytes())
    results = {name: {epsilon: dict(complete=True,
        metrics={mode: deepcopy(old['results'][name]['modes'][epsilon+'__'+previous]['metrics'])
                 for mode, previous in (('warm', 'warm'), ('full', 'warm'), ('cold', 'every-packet'))},
        statistics={'packets': old['results'][name]['modes'][epsilon+'__warm']['statistics']['packets']})
        for epsilon in ('1e-09', '1e-11')} for name in CASES}
    return dict(complete=True, runtime_modified=False, production_eligible=False,
        protocol='docs/ias15-full-suite-protocol.md',
        requests=dict.fromkeys(CASES), origins=dict.fromkeys(CASES), results=results,
        aggregate=dict(attempted=18, completed=18, passed=dict(warm=18, full=18, cold=13),
                       full_state_gate_passed=True, packets=2244))


@pytest.mark.parametrize('mutation', ['missing-case', 'missing-epsilon', 'incomplete', 'false-pass', 'runtime', 'aggregate'])
def test_report_does_not_hide_missing_variants_or_failed_gates(complete_report, mutation):
    report = complete_report
    if mutation == 'missing-case':
        del report['results'][CASES[-1]]
    elif mutation == 'missing-epsilon':
        del report['results'][CASES[-1]]['1e-11']
    elif mutation == 'incomplete':
        report['results'][CASES[-1]]['1e-11']['complete'] = False
    elif mutation == 'false-pass':
        report['results']['holdout_original']['1e-09']['metrics']['cold']['checks_passed'] = True
    elif mutation == 'runtime':
        report['runtime_modified'] = True
    else:
        report['aggregate']['full_state_gate_passed'] = False
    with pytest.raises(ValueError):
        validate_report(report)


def test_preserved_cold_failures_do_not_disqualify_separate_full_gate(complete_report):
    result = validate_report(complete_report)
    assert result['full_state_gate_passed'] and result['passed'] == dict(warm=18, full=18, cold=13)


@pytest.fixture(scope='module')
def packet():
    report = json.loads((ROOT/'docs/ias15-full-state-validation.json').read_bytes())
    with np.load(ROOT/'docs/ias15-full-state-samples.npz', allow_pickle=False) as archive:
        prefix = '1e-09__'
        return dict(warm=base64.b64decode(str(archive[prefix+'warm_binary_base64'][1])),
            full=base64.b64decode(str(archive[prefix+'full_binary_base64'][1])),
            text_warm=str(archive[prefix+'warm_physical_json'][1]),
            text_full=str(archive[prefix+'full_physical_json'][1]),
            case=dict(origin=report['origin'], request=report['request']),
            epoch=float(archive[prefix+'packet_endpoints'][1]),
            state=archive[prefix+'packet_states'][1].copy(), epsilon=1e-9, initial=False)


@pytest.mark.parametrize('mutation', ['G', 'missing-buffer', 'short-buffer', 'nonfinite-buffer', 'pointer', 'epoch', 'disagreement'])
def test_embedded_payload_guards_even_when_both_controls_share_corruption(packet, mutation):
    args = dict(packet)
    if mutation == 'epoch':
        args['epoch'] += 1.
    else:
        for mode in ('warm', 'full'):
            if mutation == 'disagreement' and mode == 'warm':
                continue
            header, fields = parse(args[mode])
            key = PREFIX+'b'
            if mutation == 'G':
                value, = struct.unpack('=d', fields['G'])
                fields['G'] = struct.pack('=d', value*2)
            elif mutation == 'missing-buffer':
                del fields[key]
            elif mutation == 'short-buffer':
                fields[key] = fields[key][:-8]
            elif mutation == 'nonfinite-buffer':
                fields[key] = struct.pack('=d', float('nan'))+fields[key][8:]
            elif mutation == 'pointer':
                raw = bytearray(fields['particles'])
                struct.pack_into('=Q', raw, 96, 1)
                fields['particles'] = bytes(raw)
            else:
                raw = bytearray(fields[key])
                raw[0] ^= 1
                fields[key] = bytes(raw)
            args[mode] = pack(header, fields)
    with pytest.raises(ValueError):
        validate_pair(**args)


def test_prior_pilot_packet_is_valid(packet):
    validate_pair(**packet)


@pytest.mark.parametrize('artifact', ['report', 'npz', 'source-zip', 'partial-directory'])
def test_existing_output_or_partial_results_are_preserved(tmp_path, monkeypatch, artifact):
    import scripts.assess_ias15_full_suite as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    output = tmp_path/'.tools'/'run.json'
    output.parent.mkdir()
    target = {'report': output, 'npz': output.with_suffix('.npz'),
              'source-zip': output.with_name('run-sources.zip'),
              'partial-directory': output.with_name('run-packets')}[artifact]
    if artifact == 'partial-directory':
        target.mkdir()
        (target/'last-committed.bin').write_bytes(b'valuable prior result')
    else:
        target.write_bytes(b'valuable prior result')
    monkeypatch.setattr(module, 'load_cases', lambda: pytest.fail('Input should not be read before output guard'))
    with pytest.raises(FileExistsError):
        run(output, tmp_path/'absent-library')
    assert target.exists()
    assert (target/'last-committed.bin' if target.is_dir() else target).read_bytes() == b'valuable prior result'


def test_public_full_suite_replays_all_cases_and_preserves_failures():
    result = replay()
    assert result['cases'] == 9 and result['variants'] == 18
    assert result['packets'] == 2244 and result['archived_snapshots'] == 4524
    assert result['arrays'] == 252
    assert result['passed'] == dict(warm=18, full=18, cold=13)
    assert result['full_state_gate_passed'] and len(result['preserved_cold_failures']) == 5


def test_variant_exceptions_preserve_partial_evidence_and_attempt_remaining_cases(tmp_path, monkeypatch):
    """Synthetic orchestration failure, no C or orbital calculation."""
    import scripts.assess_ias15_full_suite as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    for name in (module.PROTOCOL, module.LIBRARY, 'docs/ias15-restart-validation.json',
        'docs/ias15-full-state-validation.json', 'docs/ias15-full-state-samples.npz',
        'docs/ias15-archive-source-validation.json', 'scripts/ias15_full_state.py',
        'scripts/assess_ias15_full_state.py', 'scripts/assess_ias15_restart.py',
        'scripts/assess_ias15_full_suite.py', 'scripts/replay_ias15_full_suite.py',
        'tests/test_ias15_full_suite.py'):
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'synthetic test fixture')
    (tmp_path/module.LIBRARY).write_text(json.dumps({'library_files_sha256': {}}), encoding='utf-8')
    np.savez(tmp_path/'docs/ias15-restart-samples.npz')
    cases = {n: dict(request=dict(masses=[1., 2.], packet_dt=1.), initial=np.zeros((2, 6)),
                    times=np.array([0., 1.]), expected=[(0.,)*6]*2, origin=n) for n in CASES}
    monkeypatch.setattr(module, 'load_cases', lambda: (cases, {}))
    monkeypatch.setattr(module, 'old_sources', lambda: {})
    monkeypatch.setattr(module, 'load_library', lambda path: type('Library', (), {'__version__': 'synthetic'})())
    monkeypatch.setattr(module, 'library_hashes', lambda lib: {})
    monkeypatch.setattr(module, 'FullStateGuard', lambda *args: type('Guard', (), {'abi': 'synthetic'})())
    monkeypatch.setattr(module, 'simulation', lambda *args: None)
    monkeypatch.setattr(module, 'guard_checks', lambda *args: [])
    def injected_failure(case, library, epsilon, guard, directory):
        directory.mkdir(parents=True)
        (directory/'last-committed.bin').write_bytes(b'synthetic committed evidence')
        raise OSError('injected serialization failure')
    monkeypatch.setattr(module, 'paired', injected_failure)
    output = tmp_path/'.tools'/'failure-run.json'
    result = run(output, tmp_path/'unused')
    assert result['complete'] and result['aggregate']['attempted'] == 18
    assert result['aggregate']['completed'] == 0 and not result['aggregate']['full_state_gate_passed']
    assert output.with_suffix('.npz').is_file() and output.with_name('failure-run-sources.zip').is_file()
    assert all(row['failure']['message'] == 'injected serialization failure'
               for case in result['results'].values() for row in case.values())
    markers = list(output.with_name('failure-run-packets').rglob('last-committed.bin'))
    assert len(markers) == 18 and all(p.read_bytes() == b'synthetic committed evidence' for p in markers)
