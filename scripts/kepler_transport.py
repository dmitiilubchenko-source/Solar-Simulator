"""Bounded analytic error transport; public inputs, exact clocks, no runtime use."""
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path, PurePosixPath

import numpy as np

from scripts.assess_kepler_phase import ROOT
from scripts.kepler_reference import propagate
from scripts.kepler_shadow import exact_elapsed

PUBLIC_RECEIPTS = {
    'docs/rust-local-error-validation.json': 'f92c202e861fb913e0b1a973f83d01bed14260052beabc2abf75f5609753307b',
    'docs/rust-adaptive-shadow-validation.json': 'a96ae08228021abad04a1047656bd18e38d703bea2c4b2f3747d3b1a0cbf4338',
    'docs/rust-adaptive-prototype-validation.json': 'a49ec0d43894137589911dc47241b953f7ee907bcffd82bd4ab2207acff54256',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def public_path(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ValueError('Expected project-relative public path')
    path = (Path(root)/name).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Public input outside project')
    return path


def load_public_inputs(root=ROOT):
    """Verify only used public receipts/arrays; archived raw paths are irrelevant."""
    receipts, archives, hashes = [], [], {}
    for name, expected in PUBLIC_RECEIPTS.items():
        path = public_path(root, name)
        if sha(path) != expected:
            raise ValueError('Pinned public receipt changed: '+name)
        receipt = json.loads(path.read_text(encoding='utf-8'))
        if not receipt['complete'] or receipt['runtime_modified'] or receipt['production_eligible']:
            raise ValueError('Expected complete diagnostic receipt')
        archive_name = receipt['sample_archive']
        archive = public_path(root, archive_name)
        if sha(archive) != receipt['npz_sha256']:
            raise ValueError('Pinned public archive changed: '+archive_name)
        hashes.update({name: expected, archive_name: receipt['npz_sha256']})
        with np.load(archive, allow_pickle=False) as data:
            archives.append({key: data[key].copy() for key in data.files})
        receipts.append(receipt)
    if (len(receipts[0]['results']) != 9
            or any(set(r['results']) != set(receipts[0]['results']) for r in receipts[1:])):
        raise ValueError('All nine cases required')
    return receipts, archives, hashes


def accepted_nodes(case):
    """Check all attempts, preserve binary bits, and advance the clock only on accept."""
    old, trial, times, flags, metrics = (case[key] for key in ('old', 'trial', 'times', 'accepted', 'metrics'))
    count = len(flags)
    if (count == 0 or flags.dtype != np.dtype(bool) or old.shape != (count, 6)
            or trial.shape != old.shape or times.shape != (count, 3)
            or metrics.shape != (count, 14) or not all(np.isfinite(x).all() for x in (old, trial, times, metrics))):
        raise ValueError('Invalid public attempt arrays')
    bits = lambda state: state.astype('>f8').tobytes()
    states, elapsed, native_times, indices = [old[0].copy()], [D(0)], [0.], []
    current, time, clock = bits(old[0]), 0., F(0)
    for i, (previous, end, h) in enumerate(times):
        if (previous != time or not previous < end or h != end-previous
                or bits(old[i]) != current or metrics[i, 0] < 0
                or bool(flags[i]) != bool(metrics[i, 0] < 1)):
            raise ValueError('Changed attempt chronology/state/acceptance')
        if flags[i]:
            states.append(trial[i].copy())
            clock += F(float(h))
            elapsed.append(exact_elapsed(clock))
            time, current = float(end), bits(trial[i])
            native_times.append(time)
            indices.append(i)
    if not indices or indices[-1] != count-1:
        raise ValueError('Expected final accepted attempt')
    return np.asarray(states), tuple(elapsed), np.asarray(native_times), np.asarray(indices, dtype=np.int64)


def flow(state, mu, elapsed, precision):
    values = tuple(x if isinstance(x, D) else D.from_float(float(x)) for x in state)
    return sum(propagate(values[:3], values[3:], mu, elapsed, precision=precision), ())


def transport_rows(states, elapsed, mu, precision, progress=None):
    if (len(states) != len(elapsed) or len(states) < 2 or elapsed[0] != 0
            or precision not in (70, 100) or any(b <= a for a, b in zip(elapsed, elapsed[1:]))):
        raise ValueError('Expected forward accepted-node grid and precision70/100')
    horizon = F(elapsed[-1])
    result = []
    for i, (state, clock) in enumerate(zip(states, elapsed)):
        remaining = exact_elapsed(horizon-F(clock))
        result.append(flow(state, mu, remaining, precision))
        if progress is not None and i % 100 == 0:
            progress(i)
    return result


def exact_difference(left, right):
    """Bounded Decimal subtraction, verified against exact fractions."""
    with localcontext() as context:
        context.prec = 240
        result = tuple(a-b for a, b in zip(left, right))
    if len(left) != len(right) or any(F(x) != F(a)-F(b) for x, a, b in zip(result, left, right)):
        raise ArithmeticError('Difference exceeds exact diagnostic capacity')
    return result


def exact_sum(rows):
    if not rows or any(len(row) != 6 for row in rows):
        raise ValueError('Expected nonempty six-component increments')
    with localcontext() as context:
        context.prec = 240
        result = tuple(sum((row[i] for row in rows), D(0)) for i in range(6))
    if any(F(result[i]) != sum((F(row[i]) for row in rows), F(0)) for i in range(6)):
        raise ArithmeticError('Sum exceeds exact diagnostic capacity')
    return result


def norm(values):
    return sum((x*x for x in values), D(0)).sqrt()


def summarize(increments, reference):
    total = exact_sum(increments)
    with localcontext() as context:
        context.prec = 110
        speed = norm(reference[3:])
        if speed == 0:
            raise ValueError('Final reference velocity must be nonzero')
        tangent = tuple(v/speed for v in reference[3:])
        parallel = lambda row: sum((x*t for x, t in zip(row[:3], tangent)), D(0))
        phases = [parallel(row) for row in increments]
        signed = parallel(total)
        position = norm(total[:3])
        perpendicular = norm(tuple(x-signed*t for x, t in zip(total[:3], tangent)))
        return dict(total_vector=list(map(str, total)), position_metres=float(position),
            velocity_m_per_s=float(norm(total[3:])), signed_parallel_metres=str(signed),
            perpendicular_metres=float(perpendicular),
            absolute_parallel_fraction=float(abs(signed)/position) if position else None,
            positive_parallel_count=sum(p > 0 for p in phases),
            negative_parallel_count=sum(p < 0 for p in phases),
            absolute_parallel_sum_metres=float(sum(map(abs, phases), D(0))),
            position_variation_metres=float(sum((norm(row[:3]) for row in increments), D(0))),
            velocity_variation_m_per_s=float(sum((norm(row[3:]) for row in increments), D(0))))
