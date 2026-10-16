"""Prevent a model/time/IC mismatch from certifying a cached year."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import numpy as np
import pytest

from scripts.fixed_j2_year import ROOT,inputs,validate_payload,verify,historical_lineage


@pytest.fixture(scope='module')
def payload():
    seed,times,reference,baseline,_ = inputs()
    read = lambda name:json.loads((ROOT/'docs'/name).read_bytes())
    return (seed,times,reference,baseline,
        read('continuous-integration-validation.json')['outcomes']['year'],
        read('strict-profile-validation.json'),read('qualification-grid-validation.json'))


def test_public_reference_and_historical_lineage(payload):
    row = validate_payload(*payload)
    assert row['checks_passed'] and not row['source_integrals_available']
    assert row['refinement_sensitivity']['moon_relative_to_earth']['maximum_position_metres']>.003
    # Public inputs are sufficient; the optional historical proof is tested separately
    # only where those local, ignored caches already exist.
    if (ROOT/'.tools/qualification138/reference139.npz').is_file():
        assert historical_lineage()['public_raw_reference_bitexact']


@pytest.mark.parametrize('case',['physics','figures','axis','order','mass','origin','state',
    'time','shape','nan','ref_initial','uncertainty'])
def test_mismatched_payload_is_rejected(payload,case):
    seed,times,reference,baseline,year,strict,prior = deepcopy(payload)
    if case=='physics':seed = replace(seed,settings=replace(seed.settings,physics='newtonian'))
    if case=='figures':seed = replace(seed,settings=replace(seed.settings,figures=()))
    if case=='axis':
        first,*others = seed.settings.figures
        first = replace(first,axis=(0.,0.,1.))
        seed = replace(seed,settings=replace(seed.settings,figures=(first,*others)))
    if case=='order':seed.bodies[1],seed.bodies[2] = seed.bodies[2],seed.bodies[1]
    if case=='mass':seed.bodies[1] = replace(seed.bodies[1],mass=seed.bodies[1].mass*1.01)
    if case=='origin':seed = replace(seed,origin=replace(seed.origin,epoch_jd_tdb=2461322.5))
    if case=='state':baseline[0,1,0] += 1.
    if case=='time':times[1] += 1.
    if case=='shape':reference = reference[:-1]
    if case=='nan':reference[3,4,0] = np.nan
    if case=='ref_initial':reference[0,4,0] += .01
    if case=='uncertainty':year['reference_uncertainty']['all_bodies']['maximum_position_metres'] = 5.
    with pytest.raises(ValueError):validate_payload(seed,times,reference,baseline,year,strict,prior)


def test_source_hash_and_path_escape_rejected(tmp_path):
    data = tmp_path/'source.py';data.write_bytes(b'original')
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    verify({'source.py':digest},tmp_path)
    data.write_bytes(b'changed')
    with pytest.raises(ValueError,match='SHA mismatch'):verify({'source.py':digest},tmp_path)
    with pytest.raises(ValueError,match='outside project'):verify({'../source.py':digest},tmp_path)


def test_reference_failure_cannot_certify_candidate(payload):
    from scripts.assess_fixed_j2_year import metrics
    expected = payload[3]
    row = metrics(expected,expected,False)
    assert row['numerical_targets_passed'] and not row['checks_passed']


def test_per_body_and_relative_moon_gates_are_separate(payload):
    from scripts.assess_fixed_j2_year import metrics
    expected = payload[3];actual = expected.copy()
    actual[1,4,0] += .2
    row = metrics(actual,expected,True)
    assert row['all_bodies']['position_metres']<10.
    assert not row['numerical_targets_passed']
    actual = expected.copy();actual[1,9,0] += 11.
    row = metrics(actual,expected,True)
    assert row['moon_relative_to_earth']['position_metres']==0.
    assert not row['numerical_targets_passed']
