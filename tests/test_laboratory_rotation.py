"""Read-only SI views and the exact, explicitly synthetic380 demo."""
from concurrent.futures import CancelledError
import json
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from solar_simulator.storage import to_document

ROOT=Path(__file__).resolve().parents[1]


def test_profile_is_the_exact_two_body_start_of380():
    from solar_simulator.application_profiles import two_q2_demo
    expected=json.loads((ROOT/'scripts/two-q2-380-plan.json').read_bytes())['cases'][0]['initial']
    state=two_q2_demo()
    assert to_document(state)==expected
    assert state.origin is None and all('synthetic' in r.provenance for r in state.rotations)
    other=two_q2_demo(backend='rust');expected['settings']['backend']='rust'
    assert to_document(other)==expected


@pytest.mark.parametrize('count',[0,1,2])
def test_snapshot_matches_independent_inertia_solve_and_preserves_all_state(count,monkeypatch):
    from dataclasses import replace
    from solar_simulator.application_profiles import two_q2_demo
    from solar_simulator.inspection_view import prepare_inspection
    state=two_q2_demo();state=replace(state,rotations=state.rotations[:count],initial_rotations=state.initial_rotations[:count])
    doc=to_document(state);before=json.dumps(doc,sort_keys=True)
    monkeypatch.setattr('solar_simulator.experiment.advance',lambda *a:pytest.fail('Read-only inspection integrated'))
    progress=Mock();result=prepare_inspection(doc,lambda:False,progress)
    assert before==json.dumps(doc,sort_keys=True) and to_document(state)==doc
    assert len(result['rotations'])==count and result['time_seconds']==0
    assert result['numerical_reliability']['accuracy']['global_position_error_metres'] is None
    for initial,shown in zip(state.rotations,result['rotations']):
        R=Rotation.from_quat(np.roll(initial.quaternion,-1)).as_matrix()
        expected=np.linalg.solve(R@np.diag(initial.figure.moments)@R.T,initial.angular_momentum)
        assert shown['quaternion']==list(initial.quaternion)
        assert shown['angular_momentum']==list(initial.angular_momentum)
        np.testing.assert_allclose(shown['angular_velocity'],expected,rtol=2e-14,atol=1e-18)
        np.testing.assert_allclose(shown['body_to_inertial'],R,atol=1e-15)


def test_cancelled_inspection_never_calls_the_evaluator(monkeypatch):
    from solar_simulator.application_profiles import two_q2_demo
    from solar_simulator.inspection_view import prepare_inspection
    monkeypatch.setattr('solar_simulator.inspection.report',lambda *a:pytest.fail('Cancelled work evaluated'))
    with pytest.raises(CancelledError):prepare_inspection(to_document(two_q2_demo()),lambda:True,Mock())


@pytest.mark.parametrize('axes',[(0,1),(0,2),(1,2)])
def test_projected_axes_are_inertial_columns_not_an_inferred_shape(axes):
    from solar_simulator.application_profiles import two_q2_demo
    from solar_simulator.inspection_view import projected_axes
    state=two_q2_demo();original=to_document(state)
    segments=projected_axes(state,['A','B'],'A',axes)
    assert len(segments)==6
    reference=np.array(original['bodies'][0]['position'])
    for k,(body,spin) in enumerate(zip(state.bodies,state.rotations)):
        p=np.array([body.position.x,body.position.y,body.position.z])-reference
        R=Rotation.from_quat(np.roll(spin.quaternion,-1)).as_matrix()
        for j in range(3):
            expected=np.array([p,p+spin.figure.bounding_radius*R[:,j]])[:,axes]
            np.testing.assert_allclose(segments[3*k+j],expected,atol=1e-12)
    assert to_document(state)==original
    assert len(projected_axes(state,['A'],'B',axes))==3


def test_missing_native_is_explained_without_a_force_or_state_write(monkeypatch):
    from solar_simulator.application_profiles import two_q2_demo
    from solar_simulator.inspection_view import prepare_inspection
    def unavailable(*a):raise ImportError('controlled absent native')
    monkeypatch.setattr('solar_simulator.recipe._native',unavailable)
    doc=to_document(two_q2_demo(backend='rust'))
    result=prepare_inspection(doc,lambda:False,Mock())
    assert result['numerical_reliability']['execution']['native']['status']=='unavailable'
    assert doc['settings']['backend']=='rust'


def test_changed_demo_data_is_rejected_before_any_scenario_replacement(monkeypatch):
    from solar_simulator.application_profiles import two_q2_demo
    class ChangedResource:
        def joinpath(self,name):return self
        def read_bytes(self):return b'{}'
    monkeypatch.setattr('importlib.resources.files',lambda *a:ChangedResource())
    with pytest.raises(ValueError,match='изменены'):two_q2_demo()


@pytest.mark.parametrize('damage',['missing','corrupt'])
def test_before381_archive_cannot_weaken_current_source_checks(tmp_path,damage):
    import hashlib
    from scripts.release_history import LABORATORY_ARCHIVE,LABORATORY_ARCHIVE_SHA,ui_historical_sha
    name='src/solar_simulator/app.py'
    plan=json.loads((ROOT/'scripts/two-q2-380-plan.json').read_bytes())
    expected=plan['source_SHA256'][name]
    current=tmp_path/name;current.parent.mkdir(parents=True);current.write_bytes(b'changed current source')
    path=tmp_path/LABORATORY_ARCHIVE
    assert hashlib.sha256((ROOT/LABORATORY_ARCHIVE).read_bytes()).hexdigest()==LABORATORY_ARCHIVE_SHA
    if damage=='corrupt':
        path.parent.mkdir(parents=True);path.write_bytes(b'broken snapshot')
        with pytest.raises(ValueError,match='archive'):ui_historical_sha(tmp_path,name,expected)
    else:assert ui_historical_sha(tmp_path,name,expected)!=expected
