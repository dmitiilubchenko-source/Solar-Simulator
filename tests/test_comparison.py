"""Independent kinematics, lineage and exact event-side checks."""
from dataclasses import replace
import json
from math import nextafter
from pathlib import Path

import pytest

from solar_simulator.comparison import Comparison
from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.sandbox import branch_experiment
from solar_simulator.simulation import Body
from solar_simulator.trajectory import Trajectory, record_trajectory
from solar_simulator.vector3 import Vector3


def make_pair(tmp_path, *, anchor=20., parent_batch=2, child_batch=2, origin=None):
    seed = create_experiment([Body('free', 1., Vector3(3., 4., 5.), Vector3(2., -1., .5))],
                             Settings(10., integrator='dop853'), origin=origin)
    parent = advance(seed, int(anchor/10))
    body = replace(parent.bodies[0], velocity=Vector3(5., 3., -1.5))
    branch = branch_experiment(parent, replacements=(('free', body),))
    record_trajectory(seed, tmp_path/'parent', 80., packet_steps=parent_batch)
    record_trajectory(branch.child, tmp_path/'child', 60., packet_steps=child_batch,
                      parent_snapshot=branch.parent_snapshot)
    return Trajectory(tmp_path/'parent'), Trajectory(tmp_path/'child')


def test_exact_nonzero_anchor_and_independent_ballistic_vectors(tmp_path):
    parent, child = make_pair(tmp_path)
    comparison = Comparison(parent, child, event_side='after')
    assert comparison.anchor_time == 20. and comparison.times == (0., 20., 40., 60.)
    assert comparison.report()['unmatched_parent_indices'] == [0]
    for index, time in enumerate(comparison.times):
        row = comparison.sample(index)
        assert row['parent_time_seconds'] == time+20.
        values = row['bodies']['free']
        assert values['delta_position_m'] == pytest.approx([3*time, 4*time, -2*time], abs=1e-10, rel=0.)
        assert values['delta_velocity_m_per_s'] == pytest.approx([3, 4, -2], abs=1e-10, rel=0.)
        assert values['distance_m'] == pytest.approx(29**.5*time, abs=1e-10, rel=0.)
        assert values['distance_m_per_s'] == pytest.approx(29**.5, abs=1e-10, rel=0.)


def test_origin_is_inherited_by_alignment_without_rounded_jd_matching(tmp_path):
    from solar_simulator.ephemerides import EphemerisOrigin
    origin = EphemerisOrigin(2461321.5, 'Ecliptic J2000', 'Solar System Barycenter',
                             'DE441', 'a'*64, 'b'*64)
    parent, child = make_pair(tmp_path, origin=origin)
    assert child.frame(0)[0].origin is None
    comparison = Comparison(parent, child, event_side='before')
    assert comparison.origin == origin and comparison.report()['origin']['epoch_jd_tdb'] == 2461321.5
    assert comparison.sample(1)['parent_time_seconds'] == 40.


def test_unrelated_parent_with_same_times_is_rejected(tmp_path):
    parent, child = make_pair(tmp_path)
    seed = parent.frame(0)[0]
    unrelated = create_experiment([replace(seed.bodies[0], mass=2.)], seed.settings)
    record_trajectory(unrelated, tmp_path/'unrelated', 80., packet_steps=2)
    with pytest.raises(ValueError, match='Снимок родителя'):
        Comparison(Trajectory(tmp_path/'unrelated'), child, event_side='after')
    with pytest.raises(ValueError, match='bundle'):
        Comparison(parent, parent, event_side='after')


def test_partial_grids_expose_all_unmatched_frames(tmp_path):
    parent, child = make_pair(tmp_path, child_batch=3)
    comparison = Comparison(parent, child, event_side='after')
    assert comparison.times == (0., 60.)
    report = comparison.report()
    assert report['unmatched_child_indices'] == [1]
    assert report['unmatched_parent_indices'] == [0, 2, 3]


def test_one_ulp_is_not_a_common_epoch(tmp_path):
    seed = create_experiment([Body('free', 1., Vector3(0., 0., 0.), Vector3(1., 0., 0.))], Settings(1.))
    branch = branch_experiment(seed)
    record_trajectory(seed, tmp_path/'parent', 1.)
    record_trajectory(branch.child, tmp_path/'child', nextafter(1., 2.), parent_snapshot=branch.parent_snapshot)
    comparison = Comparison(Trajectory(tmp_path/'parent'), Trajectory(tmp_path/'child'), event_side='after')
    assert comparison.times == (0.,)
    assert comparison.report()['unmatched_child_indices'] == [1]


def test_fraction_subtraction_cannot_round_a_false_match(tmp_path):
    # float(2**53 + 1) rounds to 2**53. Matching by float(anchor + child_t)
    # would wrongly pair parent t=2**53 with child t=1.
    seed = create_experiment([Body('free', 1., Vector3(0., 0., 0.), Vector3(0., 0., 0.))], Settings(1.))
    seed = replace(seed, time=float(2**53))
    branch = branch_experiment(seed)
    record_trajectory(seed, tmp_path/'parent', seed.time)
    record_trajectory(branch.child, tmp_path/'child', 1., parent_snapshot=branch.parent_snapshot)
    comparison = Comparison(Trajectory(tmp_path/'parent'), Trajectory(tmp_path/'child'), event_side='after')
    assert comparison.pairs == ((0, 0),)
    assert comparison.report()['unmatched_child_indices'] == [1]


def test_relative_frame_subtracts_position_and_velocity_in_each_system(tmp_path):
    # At the edit epoch no integration is needed: independent exact vectors.
    seed = create_experiment([Body('center', 1., Vector3(10., 20., 30.), Vector3(1., 2., 3.)),
                              Body('body', 1., Vector3(13., 24., 35.), Vector3(4., 6., 8.))], Settings(1.))
    replacement = replace(seed.bodies[0], position=Vector3(100., 200., 300.), velocity=Vector3(10., 20., 30.))
    branch = branch_experiment(seed, replacements=(('center', replacement),))
    record_trajectory(seed, tmp_path/'parent', 0.)
    record_trajectory(branch.child, tmp_path/'child', 0., parent_snapshot=branch.parent_snapshot)
    comparison = Comparison(Trajectory(tmp_path/'parent'), Trajectory(tmp_path/'child'), event_side='after')
    assert comparison.sample(0)['bodies']['body']['distance_m'] == 0.
    values = comparison.sample(0, reference='center')['bodies']
    assert values['body']['delta_position_m'] == [-90., -180., -270.]
    assert values['body']['delta_velocity_m_per_s'] == [-9., -18., -27.]
    assert values['center']['distance_m'] == values['center']['distance_m_per_s'] == 0.


def test_membership_and_missing_reference_are_explicit(tmp_path):
    parent, _ = make_pair(tmp_path)
    anchor = parent.frame(1)[0]
    renamed = replace(anchor.bodies[0], name='new')
    branch = branch_experiment(anchor, removals=('free',), additions=(renamed,))
    record_trajectory(branch.child, tmp_path/'renamed', 0., parent_snapshot=branch.parent_snapshot)
    comparison = Comparison(parent, Trajectory(tmp_path/'renamed'), event_side='before')
    row = comparison.sample(0, reference='free')
    assert row['parent_only'] == ['free'] and row['child_only'] == ['new'] and row['common'] == []
    assert not row['reference_available'] and row['bodies'] == {} and row['reason'] == 'reference-missing'
    with pytest.raises(ValueError, match='Опорное тело'):
        comparison.save_report(tmp_path/'missing.json', reference='free')
    assert not (tmp_path/'missing.json').exists()


@pytest.mark.parametrize('side,expected', [('before', (0, 0)), ('after', (1, 1))])
def test_initial_contact_selects_requested_side_only(tmp_path, side, expected):
    seed = create_experiment([Body('left', 1., Vector3(-1., 0., 0.), Vector3(1., 0., 0.), 1.),
                              Body('right', 1., Vector3(1., 0., 0.), Vector3(-1., 0., 0.), 1.)], Settings(1.))
    branch = branch_experiment(seed)
    record_trajectory(seed, tmp_path/'parent', 2.)
    record_trajectory(branch.child, tmp_path/'child', 2., parent_snapshot=branch.parent_snapshot)
    parent, child = Trajectory(tmp_path/'parent'), Trajectory(tmp_path/'child')
    comparison = Comparison(parent, child, event_side=side)
    assert comparison.pairs == (expected,) and comparison.times == (0.,)
    assert comparison.sample(0)['bodies']['left']['distance_m'] == 0.


def test_comparison_never_calls_solver_or_modifies_recordings(tmp_path, monkeypatch):
    parent, child = make_pair(tmp_path)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')}
    def forbidden(*args, **kwargs):
        raise AssertionError('Comparison called solver')
    monkeypatch.setattr('solar_simulator.trajectory.advance_towards', forbidden)
    monkeypatch.setattr('solar_simulator.experiment.advance', forbidden)
    comparison = Comparison(parent, child, event_side='before')
    comparison.save_report(tmp_path/'report.json')
    report = json.loads((tmp_path/'report.json').read_bytes())
    assert len(report['samples']) == 4 and report['event_side'] == 'before'
    for directory in (parent.directory, child.directory):
        with pytest.raises(ValueError, match='вне обеих'):
            comparison.save_report(directory/'manifest.json')
    assert all(Path(p).read_bytes() == raw for p, raw in before.items())


def test_cli_comparison_exports_json_without_gui_or_solver(tmp_path, capsys):
    from solar_simulator.commands import main
    parent, child = make_pair(tmp_path)
    output = tmp_path/'comparison.json'
    assert main(['compare-trajectories', str(parent.directory), str(child.directory), str(output),
                 '--event-side', 'after', '--reference', 'free']) == 0
    assert json.loads(capsys.readouterr().out)['matched_epochs'] == 4
    assert json.loads(output.read_bytes())['samples'][1]['bodies']['free']['distance_m'] == 0.


def test_recording_of_resumed_child_keeps_original_branch_epoch(tmp_path):
    parent, child = make_pair(tmp_path)
    resumed, snapshot = child.frame(1)
    record_trajectory(resumed, tmp_path/'resumed', 60., packet_steps=2, parent_snapshot=snapshot)
    comparison = Comparison(parent, Trajectory(tmp_path/'resumed'), event_side='after')
    assert comparison.times == (20., 40., 60.) and comparison.anchor_time == 20.
    assert comparison.sample(0)['parent_time_seconds'] == 40.


def test_missing_pre_event_frame_is_not_replaced_with_post_event_frame(tmp_path):
    seed = create_experiment([Body('left', 1., Vector3(-1., 0., 0.), Vector3(1., 0., 0.), 1.),
                              Body('right', 1., Vector3(1., 0., 0.), Vector3(-1., 0., 0.), 1.)], Settings(1.))
    branch = branch_experiment(seed)
    record_trajectory(seed, tmp_path/'parent', 2.)
    record_trajectory(branch.child, tmp_path/'child', 2., parent_snapshot=branch.parent_snapshot)
    child = Trajectory(tmp_path/'child')
    post, snapshot = child.frame(1)
    record_trajectory(post, tmp_path/'post-only', 2., parent_snapshot=snapshot)
    parent = Trajectory(tmp_path/'parent')
    post_only = Trajectory(tmp_path/'post-only')
    assert Comparison(parent, post_only, event_side='after').pairs == ((1, 0),)
    with pytest.raises(ValueError, match='Нет совпадающих'):
        Comparison(parent, post_only, event_side='before')


def test_reference_disappearing_after_merge_leaves_a_gap(tmp_path):
    seed = create_experiment([Body('left', 1., Vector3(-5., 0., 0.), Vector3(1., 0., 0.), 1.),
                              Body('right', 1., Vector3(5., 0., 0.), Vector3(-1., 0., 0.), 1.)],
                             Settings(3., contact_mode='merge'))
    branch = branch_experiment(seed)
    record_trajectory(seed, tmp_path/'parent', 10.25, packet_steps=2)
    record_trajectory(branch.child, tmp_path/'child', 10.25, packet_steps=2, parent_snapshot=branch.parent_snapshot)
    comparison = Comparison(Trajectory(tmp_path/'parent'), Trajectory(tmp_path/'child'), event_side='after')
    report = comparison.report(reference='left')
    assert report['samples'][0]['reference_available']
    assert not report['samples'][-1]['reference_available']
    assert report['samples'][-1]['bodies'] == {} and report['samples'][-1]['reason'] == 'reference-missing'
    comparison.save_report(tmp_path/'gaps.json', reference='left')


def test_overflow_does_not_replace_an_existing_report(tmp_path):
    seed = create_experiment([Body('free', 1., Vector3(1e308, 0., 0.), Vector3(0., 0., 0.))], Settings(1.))
    branch = branch_experiment(seed, replacements=(('free', replace(seed.bodies[0], position=Vector3(-1e308, 0., 0.))),))
    record_trajectory(seed, tmp_path/'parent', 0.)
    record_trajectory(branch.child, tmp_path/'child', 0., parent_snapshot=branch.parent_snapshot)
    comparison = Comparison(Trajectory(tmp_path/'parent'), Trajectory(tmp_path/'child'), event_side='after')
    output = tmp_path/'report.json'
    output.write_bytes(b'original user report')
    with pytest.raises(ValueError, match='Переполнение'):
        comparison.save_report(output)
    assert output.read_bytes() == b'original user report'


def test_empty_intersection_is_explicit_and_event_side_is_required(tmp_path):
    parent, child = make_pair(tmp_path)
    state, snapshot = child.frame(0)
    resumed = advance(state, 1)
    record_trajectory(resumed, tmp_path/'odd-grid', 50., packet_steps=2, parent_snapshot=snapshot)
    with pytest.raises(ValueError, match='Нет совпадающих'):
        Comparison(parent, Trajectory(tmp_path/'odd-grid'), event_side='after')
    with pytest.raises(ValueError, match='сторону'):
        Comparison(parent, child, event_side='nearest')


def test_changed_settings_are_reported_without_rejecting_a_valid_v2_branch(tmp_path):
    parent, child = make_pair(tmp_path)
    state, snapshot = child.frame(0)
    state = replace(state, settings=replace(state.settings, dt=5.))
    record_trajectory(state, tmp_path/'v2', 60., packet_steps=4, parent_snapshot=snapshot)
    comparison = Comparison(parent, Trajectory(tmp_path/'v2'), event_side='after')
    report = comparison.report()
    assert report['parent_settings']['dt'] == 10. and report['child_settings']['dt'] == 5.
    assert comparison.times == (0., 20., 40., 60.)
    assert [change['name'] for change in report['changes']] == ['free']
