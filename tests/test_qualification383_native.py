"""Mandatory real-native preparation checks; run in desktop-native CI, no skip."""
from copy import deepcopy
import json
import pytest
from scripts import validate_two_q2_380 as rotation
from test_qualification383 import current_sources,sealed


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
