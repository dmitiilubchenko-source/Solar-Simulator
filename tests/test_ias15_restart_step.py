import hashlib
import json
from math import pi, sqrt
from pathlib import Path

import numpy as np
import pytest

from scripts.assess_ias15_restart_step import step_sidecar, restore_step, step_trajectory, run, RECIPES
from scripts.ias15_reference import load_library
from scripts.ias15_restart import bits, trajectory
from solar_simulator.simulation import G


@pytest.fixture
def library():
    path = Path(__file__).resolve().parents[1]/'.tools/ias15165/dependency'
    if path.is_dir():
        return load_library(path)
    pytest.importorskip('rebound', reason='Optional isolated IAS15 research package is absent')
    return load_library()


def request():
    mass, radius = 1e20, 1e7
    rate = sqrt(2*G*mass/radius**3)
    period = 2*pi/rate
    return dict(masses=[mass, mass], states=[[-radius/2, 0., 0., 0., -.3*radius*rate, -.4*radius*rate],
        [radius/2, 0., 0., 0., .3*radius*rate, .4*radius*rate]],
        times=[0., period/4, period/2, period, 2*period], packet_dt=period/50), rate


@pytest.mark.parametrize('recipe', RECIPES)
@pytest.mark.parametrize('epsilon', [1e-9, 1e-11])
def test_both_step_recipes_against_independent_tilted_circle(library, recipe, epsilon):
    req, rate = request()
    values, stats, data = step_trajectory(req, library, epsilon, recipe, 'circle')
    for time, row in zip(req['times'], values):
        expected = 1e7*np.array([np.cos(rate*time), .6*np.sin(rate*time), .8*np.sin(rate*time)])
        assert np.linalg.norm((row[1]-row[0])[:3]-expected) < 1e-3
    proposals = [restore_step(str(s), str(h), float(t), epsilon, 'circle') for s,h,t in
                 zip(data['step_json'], data['step_sha256'], data['packet_endpoints'])]
    used = data['restart_used_dt']
    assert len(used) == stats['packets']
    if recipe == 'reset':
        assert bits(used) == bits([req['packet_dt']/200]*len(used))
        old = trajectory(req['masses'], req['states'], req['times'], req['packet_dt'], library,
                         epsilon, 'every-packet', 'circle')
        assert bits(old[0]) == bits(values)
        for field in old[2]:
            assert np.array_equal(old[2][field], data[field])
    else:
        assert bits(used) == bits(proposals[:-1])


def test_step_sidecar_rejects_damage_and_wrong_time_or_origin():
    raw, digest = step_sidecar(3.125, 0.0625, 1e-9, 'input')
    assert restore_step(raw, digest, 3.125, 1e-9, 'input') == .0625
    for time, epsilon, origin in ((4., 1e-9, 'input'), (3.125, 1e-11, 'input'), (3.125, 1e-9, 'wrong')):
        with pytest.raises(ValueError):
            restore_step(raw, digest, time, epsilon, origin)
    document = json.loads(raw)
    document['dt'] = -1.
    changed = json.dumps(document)
    with pytest.raises(ValueError, match='SHA'):
        restore_step(changed, digest, 3.125, 1e-9, 'input')
    with pytest.raises(ValueError, match='value'):
        restore_step(changed, hashlib.sha256(changed.encode()).hexdigest(), 3.125, 1e-9, 'input')


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_previous_step_audits_cannot_be_overwritten(tmp_path, suffix):
    output = tmp_path/'result.json'
    output.with_suffix(suffix).write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        run(output, tmp_path, tmp_path)
    assert output.with_suffix(suffix).read_bytes() == b'keep'
