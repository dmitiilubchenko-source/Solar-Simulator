"""Independent epoch arithmetic and failure controls for annual research evidence."""
from copy import deepcopy
import json

import numpy as np
import pytest

from scripts import assess_free_lunar_year as audit


def series():
    return dict(position_m=np.zeros((1462,10)),velocity_m_s=np.zeros((1462,10)),
        pair_m=np.zeros(1462),orientation_rad=np.zeros(1462),subearth_angles_rad=np.zeros((1462,2)),
        subearth_residual_rad=np.zeros((1462,2)))


def comparison():
    return dict(per_body_metres=[0.]*10,all_body_metres=0.,pair_metres=0.,velocity_m_s=0.,
        attitude_frobenius=0.,spin_relative_initial=0.)


def valid_evidence():
    group = audit.series_statistics(series(),np.ones(1462,dtype=bool))
    a = dict(jobs={},external={},prefixes={},windows={},previous96={},comparisons={})
    for name in audit.short.JOBS:
        a['jobs'][name] = dict(samples=1462,raw_rotation_defect=0.,balances=dict(checks_passed=True,
            source_visibility_qualified=False,source_integrals={key:{} for key in ('pn2','pn_q','fixed_axes_torque')},
            raw=dict(energy=0.,momentum=0.,angular=0.),corrected=dict(energy=0.,momentum=0.,angular=0.),
            precision_rows=[dict(index=i,maximum_scaled=0.) for i in (0,182,365,547,730,913,1095,1278,1461)]))
        a['external'][name] = deepcopy(group)
        a['prefixes'][name] = {str(day):dict(deepcopy(group),samples=int(day*4)+1) for day in audit.PREFIX_DAYS}
        a['windows'][name] = {f'{x}-{y}':dict(deepcopy(group),samples=int((y-x)*4)+1) for x,y in audit.WINDOWS}
        a['previous96'][name] = comparison()
    a['comparisons'] = {key:comparison() for key in audit.short.LIMITS}
    return dict(complete=True,samples=1462,duration_seconds=31557600.,times_seconds=audit.TIMES.tolist(),
        jobs={name:dict(samples=1462) for name in audit.short.JOBS},initial_bridge=dict(checks_passed=True),analysis=a,
        runtime_modified=False,parameters_fitted=False,previous_trajectories_used_for_propagation=False,
        future_orientation_in_rhs=False,annual_accuracy_qualified=False,physical_PN_lunar_mapping_certified=False,network_used=False)


def test_julian_year_grid_includes_final_quarter_day_and_precision_endpoints():
    assert len(audit.TIMES) == 1462 and audit.TIMES[0] == 0.
    assert audit.TIMES[-1] == 365.25*24*3600 == 31557600.
    np.testing.assert_array_equal(np.diff(audit.TIMES),np.full(1461,6*3600.))
    assert audit.PRECISION_INDICES == [0,182,365,547,730,913,1095,1278,1461]


@pytest.mark.parametrize('bad',['short','shift','duplicate','nan'])
def test_wrong_annual_grid_is_rejected(bad):
    t = audit.TIMES.copy()
    if bad == 'short':t = t[:-1]
    if bad == 'shift':t[12] += 1.
    if bad == 'duplicate':t[-1] = t[-2]
    if bad == 'nan':t[8] = np.nan
    with pytest.raises(ValueError,match='1462 exact'):audit.validate_grid(t)


def test_shared_windows_and_short_final_window_do_not_drop_boundary_or_double_global_rms():
    data = series(); data['pair_m'][1152] = 123.
    windows = [audit.series_statistics(data,(audit.TIMES >= x*86400)&(audit.TIMES <= y*86400))
        for x,y in audit.WINDOWS]
    assert [r['samples'] for r in windows] == [385,385,385,310]
    assert [r['pair_maximum_metres'] for r in windows] == [0.,0.,123.,123.]
    whole = audit.series_statistics(data,np.ones(1462,dtype=bool))
    assert whole['pair_rms_metres'] == pytest.approx(123/np.sqrt(1462))


@pytest.mark.parametrize('bad',['body','nan','channel','mask'])
def test_missing_or_nonfinite_annual_channels_are_rejected(bad):
    data = series(); mask = np.ones(1462,dtype=bool)
    if bad == 'body':data['position_m'] = data['position_m'][:,:9]
    if bad == 'nan':data['orientation_rad'][-1] = np.nan
    if bad == 'channel':data.pop('subearth_residual_rad')
    if bad == 'mask':mask[-1] = False; mask = mask[:-1]
    with pytest.raises(ValueError):audit.series_statistics(data,mask)


def test_external_goal_failure_remains_separate_from_numerical_qualification():
    data = series(); data['pair_m'][-1] = 2000.; data['position_m'][-1,-1] = 20000.
    row = audit.series_statistics(data,np.ones(1462,dtype=bool))
    assert row['sampled_10km_1km_goal_passed'] is False
    assert row['pair_maximum_metres'] == 2000. and row['bodies']['Neptune']['maximum_metres'] == 20000.
    report = valid_evidence(); report['analysis']['external']['tight'] = row
    assert audit.qualification(report)


@pytest.mark.parametrize('bad',['missing_body','nan_body','prefix','precision','noether','reference','flag','initial_bridge','raw','angle'])
def test_true_flags_cannot_hide_incomplete_or_failed_evidence(bad):
    r = valid_evidence(); assert audit.qualification(r)
    a = r['analysis']
    if bad == 'missing_body':a['external']['tight']['bodies'].pop('Neptune')
    if bad == 'nan_body':a['external']['tight']['bodies']['Neptune']['maximum_metres'] = np.nan
    if bad == 'prefix':a['previous96']['nominal']['pair_metres'] = .02
    if bad == 'precision':a['jobs']['nominal']['balances']['precision_rows'][-1]['index'] -= 1
    if bad == 'noether':a['jobs']['nominal']['balances']['corrected']['angular'] = 2e-11
    if bad == 'reference':a['comparisons']['independent']['pair_metres'] = .2
    if bad == 'flag':r['future_orientation_in_rhs'] = True
    if bad == 'initial_bridge':r['initial_bridge']['checks_passed'] = False
    if bad == 'raw':a['jobs']['reference_tight']['raw_rotation_defect'] = 2e-8
    if bad == 'angle':a['external']['nominal']['subearth_residual_max_rad'][1] = np.nan
    assert not audit.qualification(r)


def test_fresh_guard_runs_before_missing_inputs_and_preserves_failure(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'ROOT',tmp_path)
    output = tmp_path/'.tools'/'failed'; output.parent.mkdir(); output.with_suffix('.json').write_text('failure')
    with pytest.raises(ValueError,match='preserve failures'):audit.run(output,tmp_path/'absent',tmp_path/'absent')
    assert output.with_suffix('.json').read_text() == 'failure'


def test_partial_trajectory_and_changed_sha_cannot_be_loaded(tmp_path):
    report = dict(jobs={})
    with pytest.raises(ValueError,match='five job'):audit.load_trajectories(tmp_path,report)
    for name in audit.short.JOBS:
        values = np.asfortranarray(np.zeros((1462,93 if name.startswith('reference') else 88)))
        p = tmp_path/(name+'.npz'); np.savez_compressed(p,states=values,times=audit.TIMES)
        report['jobs'][name] = dict(npz_sha256=audit.hashes([p]).popitem()[1])
    loaded = audit.load_trajectories(tmp_path,report)
    assert all(a.flags.f_contiguous for a in loaded.values())
    (tmp_path/'nominal.npz').write_bytes(b'changed')
    with pytest.raises(ValueError,match='SHA mismatch'):audit.load_trajectories(tmp_path,report)


def test_archived_executed_source_is_checked_independently_of_current_source(tmp_path,monkeypatch):
    source = tmp_path/'old.py'; source.write_text('original executed source')
    row = dict(checks_passed=True,source_sha256={},input_sha256={},propagation_source_sha256={'old.py':audit.hashes([source]).popitem()[1]},
        propagation_source_archives={'old.py':str(source)})
    path = tmp_path/'receipt.json'; path.write_text(json.dumps(row))
    monkeypatch.setattr(audit.months,'qualification',lambda r:True)
    monkeypatch.setattr(audit.months,'load_trajectories',lambda *a:{})
    assert audit.previous_receipt(path) == row
    source.write_text('modified')
    with pytest.raises(ValueError,match='executed propagation'):audit.previous_receipt(path)
