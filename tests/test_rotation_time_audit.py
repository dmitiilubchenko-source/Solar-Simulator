"""Predeclared criteria and immutable lunar input guard; no inferred migration."""
import json

import pytest

from scripts.assess_rotation_time import ROOT,bound_lunar_initial,evaluate


def policy():return json.loads((ROOT/'scripts/rotation-time-policy.json').read_text(encoding='utf-8'))


def test_lunar_input_is_source_bound_and_physical_mapping_unqualified():
    p = policy();cp = bound_lunar_initial(p,historical=True)
    assert cp.time==0 and cp.body_names[4]=='Moon'
    assert cp.metadata['provenance']['physical_mapping_certified'] is False
    with pytest.raises(ValueError,match='immutable'):bound_lunar_initial(dict(p,lunar_initial_checkpoint_sha256='0'*64),historical=True)
    with pytest.raises(ValueError,match='physical'):bound_lunar_initial(dict(p,physical_lunar_mapping_certified=True),historical=True)


def test_audit_rejects_incomplete_nonfinite_and_failed_negative_controls():
    p = policy();metrics = {k:(v*2 if k in p['minimum_metrics'] else v/2) for k,v in p['criteria'].items()}
    yes = {k:True for k in p['required_true']}
    assert evaluate(p,metrics,yes)[1] is True
    for k in p['minimum_metrics']:
        assert evaluate(p,dict(metrics,**{k:p['criteria'][k]/2}),yes)[1] is False
    assert evaluate(p,metrics,dict(yes,source_hashes_preserved=False))[1] is False
    for bad in [{},dict(metrics,flow_scaling_relative=float('nan')),dict(metrics,flow_scaling_relative=-1.)]:
        with pytest.raises(ValueError):evaluate(p,bad,yes)
    with pytest.raises(ValueError):evaluate(dict(p,physical_lunar_mapping_certified=True),metrics,yes)


def test_default_lunar_audit_cannot_execute_historical_checkpoint():
    with pytest.raises(ValueError,match='source hashes missing'):
        bound_lunar_initial(policy())
