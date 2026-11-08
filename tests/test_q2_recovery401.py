"""New adapter fault controls only; no historical74 tests or integrations."""
from copy import deepcopy
import pytest
from scripts.q2_interface_recovery401 import validate_legacy_point,physical_bits


@pytest.fixture
def data():
    bodies=[dict(name='A',mass=1.,radius=0.,spin=[0.,0.,0.],position=[0.,0.,0.],velocity=[0.,0.,0.]),
            dict(name='B',mass=2.,radius=0.,spin=[0.,0.,0.],position=[1.,0.,0.],velocity=[0.,0.,0.])]
    initial=dict(units='SI',time=0.,settings=dict(backend='python',dt=2.),initial=deepcopy(bodies),bodies=bodies,schema_version=9,model='SYNTHETIC-CONTROL-ONLY',origin=None)
    docs=[deepcopy(initial) for _ in range(3)]
    for t,d in zip((0.,2.,4.),docs):d['time']=t
    payload=dict(case='point',backend='python',epochs_seconds=[0.,2.,4.],documents=docs,legacy_initial={},native_calls=0,resume_exact=True)
    return payload,deepcopy(docs[1]),initial


def test_valid_synthetic_input_never_invents_missing_counters(data):
    r=validate_legacy_point(*data)
    assert r['historical_nfev'] is None and r['historical_solver_calls_measured'] is None
    assert r['physical_accuracy_certified'] is False


@pytest.mark.parametrize('damage',['epoch','backend','settings','IC','checkpoint','bool','nan','native','missing'])
def test_damaged_partial_or_foreign_result_is_rejected(data,damage):
    payload,checkpoint,initial=data
    if damage=='epoch':payload['epochs_seconds'][-1]=5.
    elif damage=='backend':payload['backend']='rust'
    elif damage=='settings':payload['documents'][2]['settings']['dt']=3.
    elif damage=='IC':payload['documents'][0]['bodies'][0]['mass']=3.
    elif damage=='checkpoint':checkpoint['time']=4.
    elif damage=='bool':payload['documents'][2]['bodies'][0]['position'][0]=True
    elif damage=='nan':payload['documents'][2]['bodies'][0]['position'][0]=float('nan')
    elif damage=='native':payload['native_calls']=True
    elif damage=='missing':payload['documents'].pop()
    with pytest.raises((ValueError,TypeError)):validate_legacy_point(payload,checkpoint,initial)


def test_binary_view_preserves_negative_zero(data):
    a=deepcopy(data[0]['documents']);b=deepcopy(a);b[1]['bodies'][0]['position'][0]=-0.
    assert physical_bits(a)!=physical_bits(b)


def test_saved_windows_tool_key_is_checked_without_rewriting_old_sha():
    from scripts.q2_interface_recovery401 import tool_digest
    assert tool_digest({'a\\b.py':'exact-old-sha'},'a/b.py')=='exact-old-sha'
    with pytest.raises(ValueError,match='Ambiguous'):tool_digest({'a\\b.py':'one','a/b.py':'two'},'a/b.py')


def test_saved_payload_paths_normalize_only_logical_references():
    from scripts.q2_interface_recovery401 import logical_path
    assert logical_path('final\\base\\point-python.json')=='final/base/point-python.json'
    with pytest.raises(ValueError):logical_path('../foreign.json')
