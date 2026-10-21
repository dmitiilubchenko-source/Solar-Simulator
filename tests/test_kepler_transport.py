from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import json
from math import cos, sin
import shutil

import numpy as np
import pytest

from scripts.assess_rust_transport import run
from scripts.kepler_transport import (
    ROOT, PUBLIC_RECEIPTS, public_path, load_public_inputs, accepted_nodes,
    flow, transport_rows, exact_difference, exact_sum, summarize,
)


def attempts():
    states = np.zeros((4, 6))
    states[:, 0] = [1., 2., 2., 3.]
    trial = states.copy()
    trial[:, 0] = [2., 9., 3., 4.]
    metrics = np.zeros((4, 14))
    metrics[:, 0] = [0.1, 2., 0.1, 0.1]
    return dict(old=states, trial=trial, metrics=metrics, accepted=np.array([True, False, True, True]),
        times=np.array([[0., .5, .5], [.5, 1., .5], [.5, 1., .5], [1., 1.1, 1.1-1.]]))


def test_rejected_states_and_steps_do_not_advance_exact_clock():
    with localcontext() as context:
        context.prec = 7
        states, elapsed, times, ids = accepted_nodes(attempts())
    assert states[:, 0].tolist() == [1., 2., 3., 4.]
    assert ids.tolist() == [0, 2, 3]
    assert times.tolist() == [0., .5, 1., 1.1]
    assert F(elapsed[-1]) == F(.5)+F(.5)+F(1.1-1.)


@pytest.mark.parametrize('damage', ['old', 'signed-zero', 'clock', 'flag', 'nan', 'final-rejected'])
def test_attempt_corruption_is_explicit(damage):
    case = attempts()
    if damage == 'old':
        case['old'][2, 0] += 1
    elif damage == 'signed-zero':
        case['old'][1, 1] = -0.
    elif damage == 'clock':
        case['times'][2, 2] = .25
    elif damage == 'flag':
        case['accepted'][1] = True
    elif damage == 'nan':
        case['trial'][0, 0] = np.nan
    else:
        case['accepted'][-1] = False
        case['metrics'][-1, 0] = 2.
    with pytest.raises(ValueError):
        accepted_nodes(case)


def test_circle_and_tilted_ellipse_semigroup_and_zero_endpoint():
    circle = tuple(map(D, (1, 0, 0, 0, 1, 0)))
    result = flow(circle, D(1), D('.5'), 100)
    assert max(abs(float(x)-y) for x, y in zip(result, (cos(.5), sin(.5), 0, -sin(.5), cos(.5), 0))) < 1e-15
    initial = tuple(map(D, ('3', '4', '0', '-.4', '.3', '.2')))
    first = flow(initial, D(10), D('.125'), 100)
    end = flow(initial, D(10), D('.425'), 100)
    combined = flow(first, D(10), D('.3'), 100)
    assert max(abs(a-b) for a, b in zip(end, combined)) < D('1e-90')
    assert flow(initial, D(10), D(0), 100) == initial
    values = transport_rows([initial, first, end], [D(0), D('.125'), D('.425')], D(10), 100)
    assert values[-1] == end
    assert all(max(abs(a-b) for a, b in zip(row, end)) < D('1e-90') for row in values)
    with pytest.raises(ValueError):
        transport_rows([initial, end], [D(0), D(0)], D(10), 100)


def test_exact_telescope_and_fixed_projection_despite_large_cancellation():
    zero = (D(0),)*6
    first = (D('1e20'), D(2), D(0), D(0), D(0), D(0))
    second = (D('-99999999999999999999.9999999999'), D(3), D(0), D(0), D(0), D(0))
    with localcontext() as context:
        context.prec = 7
        total = exact_sum([first, second])
        increments = [exact_difference(first, zero), exact_difference(total, first)]
        summary = summarize(increments, (D(0), D(0), D(0), D(1), D(0), D(0)))
    assert exact_sum(increments) == total
    assert total == (D('1e-10'), D(5), D(0), D(0), D(0), D(0))
    assert D(summary['signed_parallel_metres']) == D('1e-10')
    assert summary['perpendicular_metres'] == 5.
    assert summary['positive_parallel_count'] == summary['negative_parallel_count'] == 1
    assert summary['absolute_parallel_fraction'] == pytest.approx(2e-11)


def test_public_input_verification_works_in_another_root_and_detects_damage(tmp_path):
    import json
    for name in PUBLIC_RECEIPTS:
        receipt = json.loads((ROOT/name).read_text())
        for item in (name, receipt['sample_archive']):
            target = tmp_path/item
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/item, target)
    receipts, arrays, bindings = load_public_inputs(tmp_path)
    assert len(receipts) == len(arrays) == 3 and len(bindings) == 6
    assert len(receipts[0]['results']) == 9
    victim = tmp_path/receipts[0]['sample_archive']
    with victim.open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='archive changed'):
        load_public_inputs(tmp_path)
    shutil.copyfile(ROOT/receipts[0]['sample_archive'], victim)
    (tmp_path/next(iter(PUBLIC_RECEIPTS))).write_bytes(b'changed receipt')
    with pytest.raises(ValueError, match='receipt changed'):
        load_public_inputs(tmp_path)
    for name in ('../outside', '/outside', 'C:/outside', 'docs\\receipt.json'):
        with pytest.raises(ValueError):
            public_path(tmp_path, name)


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_previous_transport_output_is_preserved(tmp_path, suffix):
    output = tmp_path/'result.json'
    saved = output.with_suffix(suffix)
    saved.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        run(output)
    assert saved.read_bytes() == b'keep'


def test_all_published_transport_nodes_increments_and_metrics_reproduce():
    from scripts.assess_kepler_phase import differences, maximum, decimal_relative
    receipt = json.loads((ROOT/'docs/rust-transport-validation.json').read_text())
    assert receipt['complete'] and receipt['source_unchanged'] and receipt['input_unchanged']
    assert receipt['telescoping_is_identity'] and not receipt['global_error_bound']
    assert not receipt['runtime_modified'] and not receipt['production_eligible']
    archive = ROOT/receipt['sample_archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['npz_sha256']
    _, (local, coarse, original), _ = load_public_inputs()
    total_nodes = 0
    pair = lambda y: (y[:3], y[3:])
    with np.load(archive, allow_pickle=False) as data:
        for name, row in receipt['results'].items():
            case = {key: data[name+'_'+key] for key in ('native', 'elapsed', 'native_times',
                    'attempt_indices', 'transport70', 'transport100', 'increments')}
            states, elapsed, times, ids = accepted_nodes({key[len(name)+1:]: value
                for key, value in local.items() if key.startswith(name+'_')})
            np.testing.assert_array_equal(case['native'], states)
            np.testing.assert_array_equal(case['attempt_indices'], ids)
            np.testing.assert_array_equal(case['native_times'], times)
            assert tuple(map(D, case['elapsed'])) == elapsed
            low, high, increments = ([tuple(map(D, y)) for y in case[key]]
                                     for key in ('transport70', 'transport100', 'increments'))
            assert len(high) == row['nodes'] == row['accepted']+1
            assert increments == [exact_difference(b, a) for a, b in zip(high, high[1:])]
            assert exact_sum(increments) == exact_difference(high[-1], high[0])
            assert high[-1] == tuple(map(D.from_float, states[-1]))
            reference = tuple(map(D, coarse[name+'_prepared_oracle100'][-1]))
            actual = tuple(map(D, coarse[name+'_actual_oracle100'][-1]))
            assert summarize(increments, reference) == row['transported_summary']
            assert maximum([differences(pair(a), pair(b)) for a, b in zip(low, high)]) == row['precision_difference']
            assert differences(pair(high[0]), pair(reference)) == row['initial_reference_alignment']
            assert differences(pair(high[-1]), pair(reference)) == row['final_prepared_error']
            assert differences(pair(high[-1]), pair(actual)) == row['final_actual_error']
            with localcontext() as context:
                context.prec = 110
                physical = decimal_relative(original[name+'_rust'][-1])
                offset = elapsed[-1]-D.from_float(float(times[-1]))
            assert differences(pair(high[-1]), pair(physical)) == row['physical_export_difference']
            assert str(offset) == row['horizon_minus_nominal_seconds']
            total_nodes += len(high)
    assert total_nodes == 4482
