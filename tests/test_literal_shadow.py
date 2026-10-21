from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import json
from math import cos, sin

import numpy as np
import pytest

import scripts.assess_literal_shadow as subject
from scripts.assess_shadow_refinement import refined_trajectory
from scripts.kepler_shadow import trajectory
from test_kepler_shadow import header


@pytest.mark.parametrize('divisor', [1, 2, 4])
def test_driver_reproduces_legacy_binary_and_exact_elapsed(divisor):
    old = header()
    a = tuple(tuple(map(F, r)) for r in old['a'])
    b = tuple(map(F, old['b']))
    initial = tuple(map(D, (3, 4, 0, 1, 0, 0)))
    steps = [(0.5, 0.5), (1., 0.5)]
    args = (initial, steps, [0., 1.], old, D(1), 80)
    expected = trajectory(*args) if divisor == 1 else refined_trajectory(*args, divisor)
    assert subject.table_trajectory(initial, steps, [0., 1.], a, b, D(1), 80, divisor) == expected


def midpoint():
    a = [[F(0) for _ in range(12)] for _ in range(12)]
    a[1][0] = F(1, 2)
    b = [F(0)]*12
    b[1] = F(1)
    return a, b


def test_independent_free_motion_and_midpoint_oscillator(monkeypatch):
    a, b = midpoint()
    initial = tuple(map(D, (1, 0, 0, 0, 1, 0)))
    monkeypatch.setattr(subject, 'relative_rhs', lambda y, mu: y[3:]+(D(0),)*3)
    for divisor in (1, 2, 4):
        values, elapsed = subject.table_trajectory(initial, [(2., 2.)], [0., 2.], a, b, D(1), 80, divisor)
        assert values[-1] == tuple(map(D, (1, 2, 0, 0, 1, 0)))
        assert elapsed == [D(0), D(2)]
    monkeypatch.setattr(subject, 'relative_rhs', lambda y, mu: y[3:]+tuple(-v for v in y[:3]))
    steps = [(i/16, 1/16) for i in range(1, 17)]
    errors = []
    for divisor in (1, 2, 4):
        values, _ = subject.table_trajectory(initial, steps, [0., 1.], a, b, D(1), 80, divisor)
        y = values[-1]
        errors.append(((float(y[0])-cos(1))**2+(float(y[1])-sin(1))**2)**0.5)
    assert 3.9 < errors[0]/errors[1] < 4.1
    assert 3.9 < errors[1]/errors[2] < 4.1


def test_invalid_grid_precision_and_inexact_coefficient_rejected():
    a, b = midpoint()
    initial = tuple(map(D, (3, 4, 0, 1, 0, 0)))
    with pytest.raises(ValueError, match='macro grid'):
        subject.table_trajectory(initial, [(1., 0.5)], [0., 1.], a, b, D(1), 80, 1)
    for times in ([0., 0.5, 1.], [0., 1., 1.], [0., float('nan')]):
        with pytest.raises(ValueError):
            subject.table_trajectory(initial, [(1., 1.)], times, a, b, D(1), 80, 1)
    with pytest.raises(ValueError):
        subject.table_trajectory(initial, [(1., 1.)], [0., 1.], a, b, D(1), 70, 1)
    with localcontext() as context:
        context.prec = 80
        with pytest.raises(ArithmeticError, match='exact Decimal'):
            subject.exact_decimal(F(1, 3))
        assert F(subject.exact_decimal(F('0.12345678901234567890123456789'))) == F('0.12345678901234567890123456789')


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_existing_literal_output_is_preserved(tmp_path, suffix):
    output = tmp_path/'result.json'
    old = output.with_suffix(suffix)
    old.write_bytes(b'prior result')
    with pytest.raises(FileExistsError):
        subject.run(output)
    assert old.read_bytes() == b'prior result'


def test_all_published_errors_precision_and_invariants_from_decimal_arrays():
    root = subject.ROOT
    receipt = json.loads((root/'docs/dop853-literal-shadow-validation.json').read_text())
    assert receipt['complete'] and receipt['input_unchanged'] and receipt['source_unchanged']
    assert not receipt['production_eligible'] and not receipt['runtime_modified']
    assert receipt['original_rust_passed'] == 5
    assert len(receipt['results']) == 9
    archive = root/receipt['sample_archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['npz_sha256']
    cache = json.loads((root/subject.CACHE).read_text())
    decode = lambda array: [tuple(map(D, row)) for row in array]
    pair = lambda row: (row[:3], row[3:])
    with np.load(archive, allow_pickle=False) as data:
        for name, row in receipt['results'].items():
            assert set(row['variants']) == {'1', '2', '4'}
            expected = {key: decode(data[name+'_'+key+'_oracle100']) for key in ('prepared', 'actual')}
            for divisor, result in row['variants'].items():
                assert result['binary80_replay_exact']
                low, high = (decode(data[f'{name}_d{divisor}_p{p}']) for p in (50, 80))
                assert len(low) == len(high) == len(data[name+'_times'])
                assert high[0] == expected['prepared'][0]
                assert all(v.is_finite() for y in high for v in y)
                convergence = subject.maximum([subject.differences(pair(x), pair(y)) for x, y in zip(low, high)])
                assert convergence == result['precision_difference']
                drift = subject.invariant_drifts(high, D(cache['results'][name]['mu_exact']))
                assert drift == result['relative_invariants']
                for key in expected:
                    errors = [subject.differences(pair(x), pair(y)) for x, y in zip(high, expected[key])]
                    assert errors == result['sampled_'+key+'_errors']
                    assert subject.maximum(errors) == result[key+'_error']
                    assert subject.diagnostic_gate(subject.maximum(errors), drift) == result[key+'_diagnostic_gate']
