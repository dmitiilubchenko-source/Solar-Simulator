"""Frozen reference reuse has independent source/representation/state guards."""
from copy import deepcopy
import json

import numpy as np
import pytest

from scripts.assess_relative_canonical_checkpoint import verified_parent,historical_initial_relative as initial_relative,ROOT
from scripts.relative_canonical_checkpoint import velocity_export
from scripts.release_history import verify_checkpoint_history


def policy():return json.loads((ROOT/'scripts/relative-canonical-checkpoint-policy.json').read_text(encoding='utf-8'))


def test_bound_parent_initial_controls_and_reference_scope():
    p = policy();parent,arrays = verified_parent(p);cp,units,names = initial_relative(p,parent);verify_checkpoint_history(cp,ROOT)
    assert cp.body_names==tuple(names) and cp.pair.first==3 and cp.pair.second==4
    assert np.array_equal(np.array(cp.state).view(np.uint64),np.array(parent['initial_state']).view(np.uint64))
    assert arrays['reference-1']['states'].shape==(129,99)
    assert velocity_export(cp)['metadata']['provenance']['physical_mapping_certified'] is False
    control = cp.metadata['integration'];ma,md = cp.pair.masses[3:5]
    atol = np.array(control['atol']);v = parent['policy']['momentum_atol_equivalent_velocity_m_s']
    # Protocol62 fixes mass*SI_atol/model_velocity, including operation order.
    assert np.array_equal(atol[39:42],np.full(3,(ma+md)*v/units.velocity_m_s))
    assert np.array_equal(atol[42:45],np.full(3,ma*md/(ma+md)*v/units.velocity_m_s))


def test_reference_reuse_rejects_changed_input_or_claim():
    p = policy()
    with pytest.raises(ValueError,match='immutable'):verified_parent(dict(p,parent_report_sha256='0'*64))
    parent,_ = verified_parent(p);initial_relative(p,parent)
    for mutation in ['initial','units','physical']:
        altered = deepcopy(parent);changed_policy = dict(p)
        if mutation=='initial':altered['initial_state'][0]+=1e-6
        elif mutation=='units':altered['units_SI']['length_m']*=2
        else:changed_policy['physical_lunar_mapping_certified']=True
        with pytest.raises(ValueError,match='Incompatible historical'):initial_relative(changed_policy,altered)


def test_history_reader_rejects_changed_parent_solver_controls():
    p=policy();parent,_=verified_parent(p);initial_relative(p,parent)
    altered=deepcopy(parent);altered['policy']['production_rtol']*=2
    with pytest.raises(ValueError,match='historical relative solver controls'):
        initial_relative(p,altered)
