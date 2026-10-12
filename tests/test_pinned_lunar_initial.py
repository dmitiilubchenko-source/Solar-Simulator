"""Pinned dataset source binding and preservation of the conditional contract."""
import hashlib
from importlib.resources import files
import json

import numpy as np
import pytest

import scripts.pinned_lunar_initial as pinned
from scripts.lunar_initial_boundary import from_lunar_profile,PURPOSE


def test_factory_is_bitwise_direct_boundary_and_fingerprints_source_arrays():
    args = pinned.source_inputs();expected,_ = from_lunar_profile(**args,purpose=PURPOSE)
    actual,info = pinned.from_pinned_dataset(purpose=PURPOSE)
    assert np.array_equal(actual.view(np.uint64),expected.view(np.uint64))
    assert info['orbital_input']['body_names']==list(pinned.BODY_ORDER)
    assert info['orbital_input']['positions_model_sha256']==pinned.array_digest(args['positions'])
    assert info['orbital_input']['velocities_model_sha256']==pinned.array_digest(args['velocities'])
    assert info['boundary_contract']['physical_mapping_certified'] is False
    assert info['boundary_contract']['inertia_radius_time_compatibility']=='unqualified'
    assert info['orbital_input']['sha256']==pinned.DATASET_SHA256


def test_purpose_and_corrupted_bytes_rejected_before_inversion(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail('Rejected source reached inversion')
    monkeypatch.setattr(pinned,'from_lunar_profile',forbidden)
    with pytest.raises(ValueError,match='not certified'):pinned.from_pinned_dataset(purpose='physical')
    raw = files('solar_simulator.data').joinpath(pinned.DATASET_NAME).read_bytes()
    path = tmp_path/'changed.json';path.write_bytes(raw+b' ')
    with pytest.raises(ValueError,match='dataset'):pinned.from_pinned_dataset(purpose=PURPOSE,dataset_path=path)


@pytest.mark.parametrize('key',['frame','epoch_jd_tdb','center','units','vector_correction','schema','order','GM'])
def test_valid_digest_does_not_bypass_convention_and_parent_guards(tmp_path,monkeypatch,key):
    # Controlled fixture simulates a changed registry digest, not a real data update.
    data = json.loads(files('solar_simulator.data').joinpath(pinned.DATASET_NAME).read_text(encoding='utf-8'))
    if key=='order':data['bodies'][1:3] = data['bodies'][1:3][::-1]
    elif key=='GM':data['bodies'][3]['gm_m3_s2']*=1.001
    elif key=='schema':data[key] = True
    elif key=='epoch_jd_tdb':data[key]+=1
    else:data[key] = 'invalid'
    raw = json.dumps(data).encode('utf-8');path = tmp_path/'source.json';path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest();monkeypatch.setattr(pinned,'DATASET_SHA256',digest)
    original = pinned.lunar_solid_equivalent_initial
    def matched_parent():
        figure,earth,pair,profile = original();profile['parent_dataset_sha256'] = digest
        return figure,earth,pair,profile
    monkeypatch.setattr(pinned,'lunar_solid_equivalent_initial',matched_parent)
    def forbidden(*args,**kwargs):pytest.fail('Rejected conventions reached inversion')
    monkeypatch.setattr(pinned,'from_lunar_profile',forbidden)
    with pytest.raises(ValueError,match='Incompatible'):pinned.from_pinned_dataset(purpose=PURPOSE,dataset_path=path)


def test_array_digest_binds_shape_signed_zero_and_rejects_nonfinite_or_bool():
    assert pinned.array_digest([0.])!=pinned.array_digest([-0.])
    assert pinned.array_digest([[1.,2.]])!=pinned.array_digest([1.,2.])
    for value in [[True],[float('nan')],['1']]:
        with pytest.raises(ValueError):pinned.array_digest(value)
