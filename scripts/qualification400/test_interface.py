"""Explicit candidate-only tests; dev runtime does not adopt the interface400 patch."""
from copy import deepcopy
from dataclasses import replace
from unittest.mock import Mock

import pytest

from solar_simulator.application_profiles import two_q2_demo
from solar_simulator.storage import from_document,to_document


def test_two_q2_has_one_shared_scientific_warning():
    from solar_simulator.inspection import experimental_q2_warning,report
    from solar_simulator.inspection_view import prepare_inspection,rotation_text
    state=two_q2_demo();doc=to_document(state);before=deepcopy(doc)
    warning=experimental_q2_warning(state.rotations)
    for phrase in ('Эксперимент','total-degree-two','Q2–Q2','приливы','диссипация','EIH/Q2',
                   'FAIL380','two/Python','two/Rust','three/Python','граница ошибки',
                   'демосценария ещё не выполнена','реальных небесных тел'):
        assert phrase in warning
    r=report(state)['numerical_reliability'];payload=prepare_inspection(doc,lambda:False,Mock())
    assert warning in r['model']['limitations']
    assert warning in rotation_text(payload)
    assert r['qualification']['current_trajectory_certified'] is False
    assert r['accuracy']['global_position_error_metres'] is None
    assert r['accuracy']['global_velocity_error_m_per_s'] is None
    assert before==doc==to_document(state)


@pytest.mark.parametrize('count',[0,1])
def test_zero_one_q2_never_receive_two_q2_warning(count):
    from solar_simulator.inspection import experimental_q2_warning,report
    from solar_simulator.inspection_view import prepare_inspection,rotation_text
    state=two_q2_demo();state=replace(state,rotations=state.rotations[:count],initial_rotations=state.initial_rotations[:count])
    assert experimental_q2_warning(state.rotations)==''
    assert not any('FAIL380' in x for x in report(state)['numerical_reliability']['model']['limitations'])
    payload=prepare_inspection(to_document(state),lambda:False,Mock())
    assert 'FAIL380' not in rotation_text(payload)


@pytest.mark.parametrize('change',['name','time','mass'])
def test_custom_or_loaded_two_q2_does_not_get_automatic_pass(change):
    from solar_simulator.inspection import experimental_q2_warning,report
    doc=to_document(two_q2_demo())
    if change=='name':
        doc['bodies'][0]['name']='custom star';doc['initial'][0]['name']='custom star'
        doc['rotations'][0]['body']='custom star';doc['initial_rotations'][0]['body']='custom star'
        doc['settings']['relative_pair']=['custom star','B']
    elif change=='time':doc['time']=200.
    else:
        doc['bodies'][0]['mass']*=2;doc['initial'][0]['mass']*=2
        doc['rotations'][0]['figure']['mass']*=2;doc['initial_rotations'][0]['figure']['mass']*=2
    before=deepcopy(doc);state=from_document(doc);detail=report(state)['numerical_reliability']
    assert experimental_q2_warning(state.rotations) in detail['model']['limitations']
    assert detail['qualification']['current_trajectory_certified'] is False
    assert detail['qualification']['source_environment_and_packet_history_verified'] is False
    assert detail['accuracy']['global_position_error_metres'] is None
    assert doc==before==to_document(state)


def test_inspection_does_not_integrate_and_legacy_json_does_not_change(monkeypatch):
    from solar_simulator import cli,inspection
    state=two_q2_demo();before=cli.report(state);doc=to_document(state)
    monkeypatch.setattr('solar_simulator.experiment.advance',lambda *a,**kw:pytest.fail('Presentation integrated'))
    detail=inspection.report(state)
    assert {k:v for k,v in detail.items() if k!='numerical_reliability'}==before
    assert cli.report(state)==before and to_document(state)==doc


@pytest.mark.parametrize('bad',[True,float('nan'),float('inf')])
def test_invalid_user_snapshots_are_still_rejected(bad):
    doc=to_document(two_q2_demo());doc['rotations'][0]['quaternion'][0]=bad
    with pytest.raises((ValueError,TypeError)):from_document(doc)


def test_eih_fixed_j2_never_receive_two_q2_warning():
    from solar_simulator.solar_profiles import solar_sandbox
    from solar_simulator.inspection import report
    state=solar_sandbox(profile='strict',backend='python')
    detail=report(state)['numerical_reliability']
    assert not state.rotations and 'eih' in detail['model']['id']
    assert not any('FAIL380' in x for x in detail['model']['limitations'])
