"""Small reader contracts, without loading scientific runtimes."""
from copy import deepcopy
import pytest
from scripts.check_compatibility390 import audit_document,rotation_bits


def fixture():
    states=[dict(body=n,quaternion=[1.,0.,0.,0.],angular_momentum=[0.,1.,2.]) for n in ('A','B')]
    return dict(schema_version=10,origin=None,rotations=states,initial_rotations=deepcopy(states))


def test_two_full_rotation_records_are_required():
    d=fixture();audit_document(d)
    d['rotations']=d['rotations'][:1]
    with pytest.raises(ValueError):audit_document(d)


def test_self_contained_and_finite():
    d=fixture();d['rotations'][0]['quaternion'][1]=float('nan')
    with pytest.raises(ValueError):audit_document(d)
    d=fixture();d['extra']='https://example.org/input.json'
    with pytest.raises(ValueError):audit_document(d)


def test_qS_bits_include_initial_and_signed_zero():
    a=fixture();b=deepcopy(a);b['initial_rotations'][1]['quaternion'][2]=-0.
    assert a==b and rotation_bits(a)!=rotation_bits(b)
