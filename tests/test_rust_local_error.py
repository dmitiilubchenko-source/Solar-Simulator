from copy import deepcopy
from decimal import Decimal as D, localcontext
import hashlib
import json
from math import cos, sin, sqrt, ulp

import numpy as np
import pytest

import scripts.assess_rust_local_error as subject
from scripts.assess_rust_local_error import (
    estimator_norms, recorded_estimator, local_norm, local_solutions, run,
)
from test_kepler_shadow import header


def test_independent_estimator_limits_zero_and_separate_blocks():
    zero = [0.]*12
    assert estimator_norms(zero, zero, 2.) == [D(0)]*4
    e5, e3 = zero.copy(), zero.copy()
    e5[:3] = [1., 2., 2.]
    e3[3:6] = [1e50]*3  # A different block must not suppress the active one.
    e5[9:12] = [2., 4., 4.]
    result = estimator_norms(e5, e3, 2.)
    with localcontext() as context:
        context.prec = 110
        assert abs(result[0]-2*D(3).sqrt()) < D('1e-105')
        assert result[1] == result[2] == 0
        assert abs(result[3]-4*D(3).sqrt()) < D('1e-105')
    for bad in (float('nan'), -1., 0.):
        with pytest.raises(ValueError):
            estimator_norms(e5, e3, bad)


def test_local_rms_matches_independent_scaled_geometry():
    truth = (D(0),)*6
    state = tuple(map(D, (3, 8, 0, 6, 0, 0)))
    assert abs(float(local_norm(state, truth, [1., 2., 1., 2., 1., 1.]))-5/sqrt(3)) < 1e-15
    assert local_norm(truth, truth, [1.]*6) == 0
    with pytest.raises(ValueError):
        local_norm(state, truth, [0.]*6)


def synthetic():
    table = dict(e5=[1.]+[0.]*12, e3=[2.]+[0.]*12)
    row = dict(old=[0.]*12, trial=[0.]*12, k=[[0.]*12 for _ in range(13)], h=2.)
    row['k'][0][0] = 3.
    row['error'] = 18/sqrt(3*(9+0.01*36))
    config = dict(rtol=0., position_atol=1., velocity_atol=1.)
    return table, row, config


def test_recorded_estimator_uses_real_scales_and_detects_corruption():
    table, row, config = synthetic()
    scales, five, three, expected = recorded_estimator(table, row, config)
    assert scales == [1.]*12 and five[0] == 3. and three[0] == 6.
    assert abs(float(expected)-row['error']) <= 2*ulp(row['error'])
    for damage in ('estimate', 'stage', 'shape', 'scale'):
        t, r, c = deepcopy(table), deepcopy(row), deepcopy(config)
        if damage == 'estimate':
            r['error'] += 64*ulp(r['error'])
        elif damage == 'stage':
            r['k'][0][0] *= 2
        elif damage == 'shape':
            r['k'].pop()
        else:
            c['position_atol'] = 0.
        with pytest.raises(ValueError):
            recorded_estimator(t, r, c)


def test_local_oracle_and_shadow_against_analytic_circle_and_reverse_flow():
    from scripts.kepler_reference import propagate
    table = header()
    a = tuple(tuple(map(D.from_float, row)) for row in table['a'])
    b = tuple(map(D.from_float, table['b']))
    initial = tuple(map(D, (1, 0, 0, 0, 1, 0)))
    h = 1/16
    flow, shadow, uncertainty, agreement = local_solutions(initial, h, a, b, D(1))
    truth = (cos(h), sin(h), 0., -sin(h), cos(h), 0.)
    assert max(abs(float(x)-y) for x, y in zip(flow[100], truth)) < 1e-15
    assert max(abs(float(x)-y) for x, y in zip(shadow[80], truth)) < 1e-13
    back = sum(propagate(flow[100][:3], flow[100][3:], D(1), -D.from_float(h), precision=100), ())
    assert max(abs(x-y) for x, y in zip(back, initial)) < D('1e-90')
    assert uncertainty['position_metres'] < 1e-20 and agreement['velocity_m_per_s'] < 1e-26


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_old_local_audit_not_overwritten(tmp_path, suffix):
    result = tmp_path/'result.json'
    old = result.with_suffix(suffix)
    old.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        run(result)
    assert old.read_bytes() == b'keep'


def test_all_published_local_errors_and_normalized_operands_reproduce():
    root = subject.ROOT
    report = json.loads((root/'docs/rust-local-error-validation.json').read_text())
    assert report['complete'] and report['source_unchanged'] and report['input_unchanged']
    assert report['all194_coefficients_match'] and not report['global_error_bound']
    assert not report['production_eligible'] and not report['runtime_modified']
    archive = root/report['sample_archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == report['npz_sha256']
    assert len(report['results']) == 9
    assert report['source_sha256']['scripts/assess_rust_local_error.py'] == hashlib.sha256(
        (root/'scripts/assess_rust_local_error.py').read_bytes()).hexdigest()
    pair = lambda y: (y[:3], y[3:])
    totals = [0, 0]
    all_ulps = []
    with np.load(archive, allow_pickle=False) as data:
        for name, result in report['results'].items():
            case = {key: data[name+'_'+key] for key in ('accepted', 'metrics', 'flow70', 'flow100',
                    'shadow50', 'shadow80', 'trial', 'scales', 'e5', 'e3', 'times')}
            accepted = case['accepted']
            rows = case['metrics']
            for i, metrics in enumerate(rows):
                decode = lambda key: tuple(map(D, case[key][i]))
                flow70, flow100 = decode('flow70'), decode('flow100')
                shadow50, shadow80 = decode('shadow50'), decode('shadow80')
                actual = tuple(map(D.from_float, case['trial'][i]))
                assert all(x.is_finite() for values in (flow70, flow100, shadow50, shadow80) for x in values)
                scales = [float(case['scales'][i, j]) for j in subject.RELATIVE]
                expected = [metrics[0], float(max(estimator_norms(case['e5'][i].tolist(),
                    case['e3'][i].tolist(), float(case['times'][i, 2])))),
                    float(local_norm(actual, flow100, scales)), float(local_norm(shadow80, flow100, scales))]
                for x, y in ((actual, flow100), (shadow80, flow100), (actual, shadow80),
                             (flow70, flow100), (shadow50, shadow80)):
                    error = subject.differences(pair(x), pair(y))
                    expected.extend((error['position_metres'], error['velocity_m_per_s']))
                np.testing.assert_array_equal(metrics, expected)
                all_ulps.append(abs(metrics[0]-metrics[1])/ulp(float(metrics[0])))
            for label, mask in (('accepted', accepted), ('rejected', ~accepted)):
                values = rows[mask]
                assert len(values) == result[label]['count']
                if len(values):
                    assert dict(zip(subject.METRICS, map(float, values.max(axis=0)))) == result[label]['maxima']
                assert np.count_nonzero(values[:, 2] > 1) == result[label]['native_norm_above_one']
                assert np.count_nonzero(values[:, 3] > 1) == result[label]['shadow_norm_above_one']
            comparison = report['derived_from_sample_archive']['per_case'][name]
            ids = np.flatnonzero(accepted & (rows[:, 0] > 0))
            ratios = rows[ids, 2]/rows[ids, 0]
            worst = int(ids[np.argmax(ratios)])
            assert comparison['accepted_norm_above_estimate'] == np.count_nonzero(rows[accepted, 2] > rows[accepted, 0])
            assert comparison['accepted_zero_estimate'] == np.count_nonzero(rows[accepted, 0] == 0)
            assert comparison['median_native_to_estimate_ratio'] == float(np.median(ratios))
            assert comparison['worst_native_to_estimate_ratio'] == dict(attempt_index=worst,
                ratio=float(rows[worst, 2]/rows[worst, 0]), recorded_estimate=float(rows[worst, 0]),
                measured_norm=float(rows[worst, 2]), time=float(case['times'][worst, 0]),
                h=float(case['times'][worst, 2]))
            totals[0] += int(accepted.sum())
            totals[1] += int((~accepted).sum())
    assert totals == [4473, 99]
    assert max(all_ulps) == report['derived_from_sample_archive']['maximum_estimator_difference_ulps']
