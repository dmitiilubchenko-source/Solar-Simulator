"""Geometric limits and evidence guards for the unchanged 96-day rotor model."""
import json
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts import assess_free_lunar_months as audit


def series():
    return dict(position_m=np.zeros((385,10)),velocity_m_s=np.zeros((385,10)),
        pair_m=np.zeros(385),orientation_rad=np.zeros(385),subearth_angles_rad=np.zeros((385,2)),
        subearth_residual_rad=np.zeros((385,2)))


def test_body_longitude_has_analytic_rotating_axis_sign_and_no_branch_jump():
    theta = np.linspace(0.,4*np.pi,385)
    r = Rotation.from_rotvec(np.c_[np.zeros(385),np.zeros(385),theta]).as_matrix()
    angles = audit.body_angles(r,np.tile([-1.,0.,0.],(385,1)))
    np.testing.assert_allclose(angles[:,0],-theta,rtol=0,atol=3e-15)
    np.testing.assert_array_equal(angles[:,1],np.zeros(385))


def test_body_latitude_and_longitude_match_known_cartesian_direction():
    longitude,latitude = np.array([3.1,-3.1]),np.array([.2,-.3])
    direction = np.c_[np.cos(latitude)*np.cos(longitude),np.cos(latitude)*np.sin(longitude),np.sin(latitude)]
    actual = audit.body_angles(np.tile(np.eye(3),(2,1,1)),-direction)
    np.testing.assert_allclose(actual[:,0],[3.1,2*np.pi-3.1],atol=1e-15,rtol=0)
    np.testing.assert_allclose(actual[:,1],latitude,atol=1e-15,rtol=0)
    delta = audit.circular_difference([np.pi-1e-8],[-np.pi+1e-8])
    assert delta[0] == pytest.approx(-2e-8,rel=1e-7,abs=0.)


def test_shared_window_boundary_is_retained_without_changing_global_sample_count():
    data = series(); data['pair_m'][256] = 123.
    rows = [audit.series_statistics(data,(audit.TIMES >= start*audit.DAY)&(audit.TIMES <= (start+32)*audit.DAY))
        for start in (0,32,64)]
    assert [r['samples'] for r in rows] == [129,129,129]
    assert [r['pair_maximum_metres'] for r in rows] == [0.,123.,123.]
    all_rows = audit.series_statistics(data,np.ones(385,dtype=bool))
    assert all_rows['samples'] == 385
    assert all_rows['pair_rms_metres'] == pytest.approx(123/np.sqrt(385))


@pytest.mark.parametrize('bad',['short','duplicate','shift'])
def test_exact_epoch_inventory_rejects_wrong_duration_or_epoch(bad):
    times = audit.TIMES.copy()
    if bad == 'short':times = times[:-1]
    if bad == 'duplicate':times[-1] = times[-2]
    if bad == 'shift':times[12] += 1.
    with pytest.raises(ValueError,match='385 exact'):audit.validate_grid(times)


@pytest.mark.parametrize('bad',['missing_neptune','nan','missing_channel'])
def test_external_statistics_rejects_incomplete_or_nonfinite_channels(bad):
    data = series()
    if bad == 'missing_neptune':data['position_m'] = data['position_m'][:,:9]
    if bad == 'nan':data['subearth_angles_rad'][17,0] = np.nan
    if bad == 'missing_channel':data.pop('velocity_m_s')
    with pytest.raises(ValueError,match='finite external'):audit.series_statistics(data,np.ones(385,dtype=bool))


def test_large_jpl_residual_is_recorded_as_failed_goal_not_filtered():
    data = series(); data['pair_m'][192] = 2000.; data['position_m'][192,4] = 20000.
    row = audit.series_statistics(data,np.ones(385,dtype=bool))
    assert row['sampled_10km_1km_goal_passed'] is False
    assert row['pair_maximum_metres'] == 2000. and row['bodies']['Moon']['maximum_metres'] == 20000.
    assert row['annual_accuracy_qualified'] is False


def test_one_bad_body_cannot_be_hidden_by_aggregate_comparison_scalar():
    row = dict(per_body_metres=[0.]*10,all_body_metres=0.,pair_metres=0.,velocity_m_s=0.,
        attitude_frobenius=0.,spin_relative_initial=0.)
    assert audit.orbit_comparison_qualified(row,audit.PREFIX_LIMITS)
    row['per_body_metres'][-1] = 100.
    assert not audit.orbit_comparison_qualified(row,audit.PREFIX_LIMITS)
    row['per_body_metres'][-1] = np.nan
    assert not audit.orbit_comparison_qualified(row,audit.PREFIX_LIMITS)


def test_reanalysis_rejects_missing_forecasts_before_readout():
    with pytest.raises(ValueError,match='five forecasts'):audit.analyse({},None,None,audit.TIMES,None,None)
    assert not audit.qualification(dict(complete=True,samples=385,duration_seconds=96*audit.DAY,
        times_seconds=audit.TIMES.tolist(),initial_bridge=dict(checks_passed=True),analysis={}))


def test_existing_failed_receipt_cannot_be_overwritten_before_input_read(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'ROOT',tmp_path)
    output = tmp_path/'.tools'/'failed'; output.parent.mkdir(); output.with_suffix('.json').write_text('failed')
    with pytest.raises(ValueError,match='preserve failures'):audit.run(output,tmp_path/'missing',tmp_path/'old')
    assert output.with_suffix('.json').read_text() == 'failed'


def test_geometric_angle_rejects_zero_direction_and_nan():
    with pytest.raises(ValueError,match='distinct centres'):audit.body_angles(np.eye(3)[None],np.zeros((1,3)))
    with pytest.raises(ValueError,match='Finite matching'):audit.body_angles(np.eye(3)[None],np.array([[np.nan,0.,0.]]))


def test_npz_loader_preserves_stored_memory_order_for_bitwise_diagnostics(tmp_path):
    report = dict(jobs={})
    expected = {}
    for name in audit.short.JOBS:
        size = 93 if name.startswith('reference') else 88
        values = np.asfortranarray(np.arange(385*size,dtype=float).reshape(385,size))
        path = tmp_path/(name+'.npz'); np.savez_compressed(path,states=values,times=audit.TIMES)
        report['jobs'][name] = dict(npz_sha256=audit.hashes([path]).popitem()[1])
        expected[name] = values
    loaded = audit.load_trajectories(tmp_path,report)
    for name,values in loaded.items():
        assert values.flags.f_contiguous and not values.flags.c_contiguous
        np.testing.assert_array_equal(values,expected[name])
