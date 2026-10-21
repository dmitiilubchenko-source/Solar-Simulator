from decimal import Decimal as D, localcontext
import hashlib
import json
import shutil

import numpy as np
import pytest

from scripts.assess_transport_split import load_transport, split_increments, run
from scripts.kepler_transport import ROOT, exact_sum, exact_difference, summarize


def vector(x, y=0):
    return (D(x), D(y), D(0), D(0), D(0), D(0))


def test_ordered_split_keeps_signs_and_exact_identity_under_cancellation():
    nodes = [vector(0), vector(1, 2), vector(3, 5)]
    middle = [vector('1e20', -3), vector('-1e20', 9)]
    with localcontext() as context:
        context.prec = 7
        rk, native = split_increments(nodes, middle)
    assert [exact_sum([a, b]) for a, b in zip(rk, native)] == [vector(1, 2), vector(2, 3)]
    assert exact_sum([exact_sum(rk), exact_sum(native)]) == vector(3, 5)
    assert rk[0][0] > 0 and rk[1][0] < 0 and native[0][0] < 0 and native[1][0] > 0
    reference = (D(0), D(0), D(0), D(1), D(0), D(0))
    assert D(summarize(rk, reference)['signed_parallel_metres']) == D(-1)
    assert D(summarize(native, reference)['signed_parallel_metres']) == D(4)


def test_lost_or_shifted_split_nodes_are_rejected_or_change_the_bound_result():
    nodes = [vector(0), vector(1), vector(2)]
    with pytest.raises(ValueError):
        split_increments(nodes, [vector(0)])
    with pytest.raises(ValueError):
        split_increments([], [])
    a, b = split_increments(nodes, [vector(10), vector(20)])
    shifted, _ = split_increments(nodes, [vector(20), vector(10)])
    assert a != shifted
    assert exact_sum([exact_sum(a), exact_sum(b)]) == exact_difference(nodes[-1], nodes[0])


def test_transport_cache_is_portable_and_corruption_is_detected(tmp_path):
    name = 'docs/rust-transport-validation.json'
    receipt = json.loads((ROOT/name).read_text())
    paths = {name, receipt['sample_archive'], *receipt['source_sha256'], *receipt['input_sha256']}
    for item in paths:
        target = tmp_path/item
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/item, target)
    report, arrays, inputs = load_transport(tmp_path/name, root=tmp_path)
    assert len(report['results']) == 9 and len(arrays) == 9*7
    assert name in inputs and report['sample_archive'] in inputs
    archive = tmp_path/report['sample_archive']
    with archive.open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='Changed transport'):
        load_transport(tmp_path/name, root=tmp_path)
    shutil.copyfile(ROOT/report['sample_archive'], archive)
    source = tmp_path/'scripts/kepler_reference.py'
    source.write_bytes(b'changed source')
    with pytest.raises(ValueError, match='Changed transport'):
        load_transport(tmp_path/name, root=tmp_path)
    shutil.copyfile(ROOT/'scripts/kepler_reference.py', source)
    report['complete'] = False
    (tmp_path/name).write_text(json.dumps(report))
    with pytest.raises(ValueError, match='complete349'):
        load_transport(tmp_path/name, root=tmp_path)


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_previous_split_results_are_preserved(tmp_path, suffix):
    output = tmp_path/'result.json'
    previous = output.with_suffix(suffix)
    previous.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        run(output)
    assert previous.read_bytes() == b'keep'


def test_all_published_splits_semigroup_and_metrics_reproduce():
    from scripts.assess_kepler_phase import differences, maximum
    from scripts.kepler_transport import load_public_inputs
    report = json.loads((ROOT/'docs/rust-transport-split-validation.json').read_text())
    assert report['complete'] and report['source_unchanged'] and report['input_unchanged']
    assert report['ordered_split'] and not report['unique_causal_attribution']
    assert not report['runtime_modified'] and not report['production_eligible']
    archive = ROOT/report['sample_archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == report['npz_sha256']
    original, old, _ = load_transport(ROOT/'docs/rust-transport-validation.json')
    _, (_, coarse, _), _ = load_public_inputs()
    pair = lambda y: (y[:3], y[3:])
    decode = lambda array: [tuple(map(D, row)) for row in array]
    steps = 0
    with np.load(archive, allow_pickle=False) as data:
        for name, row in report['results'].items():
            case = {key: decode(data[name+'_'+key]) for key in ('middle70', 'middle100',
                    'semigroup100', 'rk_increments', 'native_increments')}
            nodes = decode(old[name+'_transport100'])
            rk, native = split_increments(nodes, case['middle100'])
            assert rk == case['rk_increments'] and native == case['native_increments']
            assert [exact_sum([a, b]) for a, b in zip(rk, native)] == decode(old[name+'_increments'])
            assert exact_sum([exact_sum(rk), exact_sum(native)]) == tuple(map(D, original['results'][name]['transported_summary']['total_vector']))
            reference = tuple(map(D, coarse[name+'_prepared_oracle100'][-1]))
            assert summarize(rk, reference) == row['rk_summary']
            assert summarize(native, reference) == row['native_summary']
            assert row['original_total'] == original['results'][name]['transported_summary']
            assert maximum([differences(pair(a), pair(b)) for a, b in zip(case['middle70'], case['middle100'])]) == row['precision_difference']
            assert maximum([differences(pair(a), pair(b)) for a, b in zip(case['semigroup100'], nodes[:-1])]) == row['semigroup_difference']
            assert len(rk) == len(native) == row['steps'] and row['all_split_identities_exact']
            steps += len(rk)
    assert steps == 4473
