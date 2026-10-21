from decimal import Decimal as D, localcontext
import hashlib
import json
import shutil

import numpy as np
import pytest

from scripts.assess_transport_order import load_split, reversed_step, order_changes, run
from scripts.assess_transport_split import split_increments
from scripts.kepler_transport import ROOT, exact_sum, exact_difference


def vector(x):
    return (D(x), D(0), D(0), D(0), D(0), D(0))


@pytest.mark.parametrize('quadratic', [False, True])
def test_independent_affine_and_quadratic_mixed_differences(quadratic):
    a, r, n = vector(1), vector(3), vector(6)
    reverse = reversed_step(a, r, n)
    assert reverse == vector(4)
    transform = (lambda y: vector(y[0]*y[0])) if quadratic else (lambda y: vector(2*y[0]+5))
    nodes = [transform(a), transform(n)]
    old_rk, old_native = split_increments(nodes, [transform(r)])
    new_native, new_rk = split_increments(nodes, [transform(reverse)])
    delta = order_changes(old_rk, old_native, new_rk, new_native)
    assert delta == [vector(12 if quadratic else 0)]
    assert exact_sum([old_rk[0], old_native[0]]) == exact_difference(nodes[-1], nodes[0])
    assert exact_sum([new_rk[0], new_native[0]]) == exact_difference(nodes[-1], nodes[0])
    if quadratic:
        assert (old_rk[0][0], old_native[0][0], new_rk[0][0], new_native[0][0]) == (8, 27, 20, 15)


def test_reversed_local_endpoint_is_exact_under_small_ambient_precision():
    with localcontext() as context:
        context.prec = 7
        exact, shadow, native = vector('1e20'), vector('100000000000000000000.0000000001'), vector('100000000000000000000.0000000003')
        reverse = reversed_step(exact, shadow, native)
        assert reverse == vector('100000000000000000000.0000000002')
        assert exact_sum([reverse, exact_difference(shadow, exact)]) == native


def test_corrupt_order_components_are_rejected():
    with pytest.raises(ValueError):
        order_changes([], [], [], [])
    with pytest.raises(ArithmeticError):
        order_changes([vector(1)], [vector(2)], [vector(2)], [vector(2)])


def test_split_cache_works_in_another_root_and_rejects_damage(tmp_path):
    name = 'docs/rust-transport-split-validation.json'
    report = json.loads((ROOT/name).read_text())
    paths = {name, report['sample_archive'], *report['source_sha256'], *report['input_sha256']}
    for item in paths:
        target = tmp_path/item
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/item, target)
    receipt, arrays, inputs = load_split(tmp_path/name, root=tmp_path)
    assert len(receipt['results']) == 9 and len(arrays) == 9*5
    assert name in inputs and report['sample_archive'] in inputs
    victim = tmp_path/report['sample_archive']
    with victim.open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='Changed split'):
        load_split(tmp_path/name, root=tmp_path)
    shutil.copyfile(ROOT/report['sample_archive'], victim)
    report['complete'] = False
    (tmp_path/name).write_text(json.dumps(report))
    with pytest.raises(ValueError, match='complete350'):
        load_split(tmp_path/name, root=tmp_path)


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_previous_order_output_is_preserved(tmp_path, suffix):
    output = tmp_path/'result.json'
    saved = output.with_suffix(suffix)
    saved.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        run(output)
    assert saved.read_bytes() == b'keep'


def test_all_published_order_changes_metrics_and_zero_endpoints_reproduce():
    from scripts.assess_kepler_phase import differences, maximum
    from scripts.assess_transport_split import load_transport
    from scripts.kepler_transport import load_public_inputs, summarize
    receipt = json.loads((ROOT/'docs/rust-transport-order-validation.json').read_text())
    assert receipt['complete'] and receipt['source_unchanged'] and receipt['input_unchanged']
    assert not receipt['runtime_modified'] and not receipt['production_eligible']
    assert not receipt['unique_causal_attribution'] and not receipt['global_error_bound']
    archive = ROOT/receipt['sample_archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['npz_sha256']
    old, old_arrays, _ = load_split(ROOT/'docs/rust-transport-split-validation.json')
    _, native_arrays, _ = load_transport(ROOT/'docs/rust-transport-validation.json')
    _, (local, coarse, _), _ = load_public_inputs()
    pair = lambda y: (y[:3], y[3:])
    decode = lambda rows: [tuple(map(D, row)) for row in rows]
    zero = (D(0),)*6
    steps = 0
    with np.load(archive, allow_pickle=False) as data:
        for name, row in receipt['results'].items():
            case = {key: decode(data[name+'_'+key]) for key in ('reverse70', 'reverse100',
                    'reverse_rk_increments', 'reverse_native_increments', 'rk_order_change')}
            nodes = decode(native_arrays[name+'_transport100'])
            native_first, rk_second = split_increments(nodes, case['reverse100'])
            assert native_first == case['reverse_native_increments'] and rk_second == case['reverse_rk_increments']
            old_rk, old_native = (decode(old_arrays[name+'_'+key]) for key in ('rk_increments', 'native_increments'))
            changes = order_changes(old_rk, old_native, rk_second, native_first)
            assert changes == case['rk_order_change'] and changes[-1] == zero
            assert exact_sum([exact_sum(rk_second), exact_sum(native_first)]) == exact_difference(nodes[-1], nodes[0])
            reference = tuple(map(D, coarse[name+'_prepared_oracle100'][-1]))
            assert summarize(rk_second, reference) == row['reverse_rk_summary']
            assert summarize(native_first, reference) == row['reverse_native_summary']
            summary = summarize(changes, reference)
            assert summary == row['change_summary']
            assert maximum([differences(pair(a), pair(b)) for a, b in zip(case['reverse70'], case['reverse100'])]) == row['precision_difference']
            assert maximum([differences(pair(y), pair(zero)) for y in changes]) == row['per_step_maximum_change']
            assert row['original_rk_summary'] == old['results'][name]['rk_summary']
            assert row['original_native_summary'] == old['results'][name]['native_summary']
            assert row['diagnostic_stability_passed'] == (summary['position_metres'] < 1e-6 and summary['velocity_m_per_s'] < 1e-12)
            index = native_arrays[name+'_attempt_indices'][-1]
            a = tuple(map(D, local[name+'_flow100'][index]))
            r = tuple(map(D, local[name+'_shadow80'][index]))
            n = tuple(map(D.from_float, local[name+'_trial'][index]))
            assert case['reverse100'][-1] == reversed_step(a, r, n)
            assert row['last_step_change_exact_zero'] and row['all_order_identities_exact']
            assert len(changes) == row['steps']
            steps += len(changes)
    assert steps == 4473
    assert receipt['all_diagnostic_stability_passed'] == all(r['diagnostic_stability_passed'] for r in receipt['results'].values())
