"""Candidate preparation must not silently relax historical qualification."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import qualify_current_runtime375 as annual
from scripts import check_runtime_reliability376 as newton
from scripts import validate_two_q2_380 as rotation


def sealed(tmp_path, value):
    path = tmp_path/'plan.json'
    path.write_text(json.dumps(value), encoding='utf8')
    return path, annual.sha(path)


def current_sources(sources):
    # Unit fault tests do not execute a scientific job or qualify native.
    # A Linux Python-only runner has no Windows-only .venv dependency paths.
    return {name:annual.sha(annual.ROOT/name) for name in sources
            if (annual.ROOT/name).is_file()}


def test_375_candidate_keeps_science_and_checks_explicit_sha(tmp_path):
    original = annual.protocol()
    candidate = deepcopy(original)
    candidate['runtime_commit'] = 'a'*40
    candidate['candidate_native'] = {'sha256': 'b'*64}
    path, digest = sealed(tmp_path, candidate)
    assert annual.protocol(path, digest) == candidate
    assert annual.protocol() == original
    with pytest.raises(ValueError, match='SHA|protocol'):
        annual.protocol(path, '0'*64)
    with pytest.raises(ValueError, match='SHA'):
        annual.protocol(path)


@pytest.mark.parametrize('field', ['criteria', 'settings', 'epochs_jd_tdb', 'input_sha256', 'origin'])
def test_375_rejects_changes_to_scientific_contract(tmp_path, field):
    candidate = deepcopy(annual.protocol())
    candidate[field] = None
    path, digest = sealed(tmp_path, candidate)
    with pytest.raises(ValueError, match='scientific'):
        annual.protocol(path, digest)


def test_376_bad_seal_rejected_before_creating_output(tmp_path):
    output = tmp_path/'result'
    with pytest.raises(ValueError, match='SHA'):
        newton.run(output, protocol_path=newton.PROTOCOL, expected_sha='0'*64)
    assert not output.exists()


def test_380_bad_seal_rejected_before_creating_output(tmp_path):
    output = tmp_path/'result'
    with pytest.raises(ValueError, match='SHA'):
        rotation.run(output, plan_path=rotation.PLAN, expected_sha='0'*64)
    assert not output.exists()


def test_380_real_environment_change_rejected(tmp_path, monkeypatch):
    from solar_simulator.recipe import runtime_fingerprint
    plan = deepcopy(json.loads(rotation.PLAN.read_bytes()))
    plan['source_SHA256'] = current_sources(plan['source_SHA256'])
    plan['environment'] = runtime_fingerprint('rust')
    path, digest = sealed(tmp_path, plan)
    old = plan['environment']['numerical_environment']['OMP_NUM_THREADS']
    monkeypatch.setenv('OMP_NUM_THREADS', '2' if old != '2' else '3')
    with pytest.raises(ValueError, match='environment'):
        rotation.verify(path, digest)


def test_375_missing_and_corrupted_inputs_are_early_errors(tmp_path):
    path = tmp_path/'input'
    path.write_bytes(b'good')
    annual.verify_inputs({'input_sha256': {'input': annual.sha(path)}, 'raw_jpl_sha256': {}}, tmp_path)
    path.write_bytes(b'bad')
    with pytest.raises(ValueError, match='input'):
        annual.verify_inputs({'input_sha256': {'input': '0'*64}, 'raw_jpl_sha256': {}}, tmp_path)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        annual.verify_inputs({'input_sha256': {'input': '0'*64}, 'raw_jpl_sha256': {}}, tmp_path)


def test_375_independent_output_rejects_reuse(tmp_path):
    folder = annual.job_folder(tmp_path/'new-work', 'current')
    marker = folder/'keep'; marker.write_bytes(b'partial-or-complete')
    with pytest.raises(FileExistsError):
        annual.job_folder(tmp_path/'new-work', 'current')
    assert marker.read_bytes() == b'partial-or-complete'


def test_incomplete_375_receipt_is_not_an_executed_job(tmp_path, monkeypatch):
    from scripts import assess_current_runtime375 as observer
    folder = tmp_path/'run-current'; folder.mkdir()
    (folder/'receipt.json').write_text(json.dumps({'protocol_sha256': observer.PROTOCOL_SHA,
        'solver_executed': False, 'driver_sha256': annual.sha(annual.__file__)}))
    monkeypatch.setattr(observer, 'WORK', tmp_path)
    with pytest.raises(ValueError, match='unexecuted'):
        observer.load_job('current', annual.protocol(),work=tmp_path)


def test_376_rejects_changed_science_before_output(tmp_path):
    p = deepcopy(json.loads(newton.PROTOCOL.read_bytes()))
    p['settings']['position_atol'] *= 10
    path, digest = sealed(tmp_path, p)
    with pytest.raises(ValueError, match='scientific'):
        newton.run(tmp_path/'result',protocol_path=path,expected_sha=digest)
    assert not (tmp_path/'result').exists()


def test_380_rejects_changed_criteria(tmp_path):
    p = deepcopy(json.loads(rotation.PLAN.read_bytes()))
    p['criteria']['energy_drift'] *= 10
    path, digest = sealed(tmp_path,p)
    with pytest.raises(ValueError, match='scientific'):
        rotation.verify(path,digest)


def test_candidate_metadata_overlay_does_not_edit_other_values(tmp_path):
    from scripts.prepare_qualification383 import METADATA, version_overlay, ROOT
    import tomllib
    for name in METADATA:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((ROOT/name).read_bytes())
    before={name:tomllib.loads((tmp_path/name).read_text()) for name in METADATA}
    changes=version_overlay(tmp_path)
    assert set(changes)==set(METADATA)
    for name in METADATA:
        actual=tomllib.loads((tmp_path/name).read_text())
        expected=before[name]
        if name.endswith('.lock'):
            for package in expected['package']:
                if package['name'] in ('solar_core','solar_native'):package['version']='0.3.3'
        elif name.endswith('pyproject.toml'):expected['project']['version']='0.3.3'
        else:expected['package']['version']='0.3.3'
        assert actual==expected


def test_history_archive_does_not_authorize_changed_live_375_source():
    from scripts.sandbox_checks.accept_sandbox import check_receipts,ROOT
    with pytest.raises(ValueError,match='changed'):
        check_receipts(ROOT)


def test_376_existing_output_is_never_reused(tmp_path):
    p=deepcopy(json.loads(newton.PROTOCOL.read_bytes()))
    p['source_SHA256']=current_sources(p['source_SHA256'])
    path,digest=sealed(tmp_path,p)
    output=tmp_path/'output';output.mkdir();(output/'keep').write_bytes(b'partial')
    with pytest.raises(FileExistsError):
        newton.run(output,protocol_path=path,expected_sha=digest)
    assert (output/'keep').read_bytes()==b'partial'


def test_380_existing_output_is_never_reused(tmp_path):
    from solar_simulator.recipe import runtime_fingerprint
    p=deepcopy(json.loads(rotation.PLAN.read_bytes()))
    p['source_SHA256']=current_sources(p['source_SHA256'])
    p['environment']=runtime_fingerprint('rust')
    path,digest=sealed(tmp_path,p)
    output=tmp_path/'output';output.mkdir();(output/'keep').write_bytes(b'partial')
    with pytest.raises(FileExistsError):
        rotation.run(output,plan_path=path,expected_sha=digest)
    assert (output/'keep').read_bytes()==b'partial'


def test_376_new_reduction_rejects_partial_before_creating_evidence(tmp_path):
    from scripts.assess_runtime_reliability376 import build
    p=deepcopy(json.loads(newton.PROTOCOL.read_bytes()))
    p['source_SHA256']=current_sources(p['source_SHA256'])
    path,digest=sealed(tmp_path,p)
    raw=tmp_path/'raw';raw.mkdir()
    (raw/'receipt.json').write_text(json.dumps({'complete':False,'failure':{'message':'stop'}}))
    report,arrays=tmp_path/'report.json',tmp_path/'states.npz'
    with pytest.raises(ValueError,match='Incomplete'):
        build(tmp_path,protocol_path=path,report_path=report,arrays_path=arrays,run_directory=raw)
    assert not report.exists() and not arrays.exists()
