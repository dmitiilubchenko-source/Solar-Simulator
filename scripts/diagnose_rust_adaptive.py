"""Analyse the frozen335 trajectories; no integrator or oracle is modified."""
import argparse
from decimal import Decimal as D, localcontext
import hashlib
import json
from pathlib import Path
import platform
from time import perf_counter

import numpy as np

from scripts.assess_kepler_holdout import CASES, holdout_fixture
from scripts.assess_kepler_phase import (ROOT, decimal_relative, differences,
                                        fixture, maximum, references)
from scripts.assess_rust_adaptive import provenance, sources
from scripts.assess_sandbox_planets import states

PROTOCOL = 'docs/rust-adaptive-diagnosis-protocol.md'
EVIDENCE = 'docs/rust-adaptive-prototype-validation.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def position_projection(actual, expected):
    """Linear along-velocity description, never an adjusted accuracy metric."""
    with localcontext() as context:
        context.prec = 110
        if (len(actual) != 6 or len(expected) != 2 or any(len(g) != 3 for g in expected)
                or any(not isinstance(x, D) or not x.is_finite()
                       for x in (*actual, *expected[0], *expected[1]))):
            raise ValueError('Expected finite Decimal relative position/velocity')
        delta = tuple(a-b for a, b in zip(actual[:3], expected[0]))
        velocity = expected[1]
        speed2 = sum(v*v for v in velocity)
        if speed2 == 0:
            raise ValueError('Along-velocity projection requires nonzero velocity')
        time_shift = sum(d*v for d, v in zip(delta, velocity))/speed2
        parallel = tuple(time_shift*v for v in velocity)
        normal = tuple(d-p for d, p in zip(delta, parallel))
        norm = lambda v: sum(x*x for x in v).sqrt()
        error, along = norm(delta), norm(parallel)
        return dict(time_shift_seconds=float(time_shift), position_metres=float(error),
                    along_velocity_metres=float(along), normal_metres=float(norm(normal)),
                    along_fraction=float(along/error) if error else None)


def alternative_bound(error, budget):
    """Reverse triangle bound; alternatives are assessed separately."""
    keys = ('position_metres', 'velocity_m_per_s')
    if any(not np.isfinite(x[k]) or x[k] < 0 for x in (error, budget) for k in keys):
        raise ValueError('Error/budget must be finite and nonnegative')
    # Reported maxima have already been rounded to binary64. Enclose those
    # rounded inputs, then round the subtraction downward; never overstate it.
    lower = {k: max(0., float(np.nextafter(
        np.nextafter(error[k], -np.inf)-np.nextafter(budget[k], np.inf), -np.inf)))
        for k in keys}
    return dict(sensitivity_maximum=budget, remaining_error_lower_bound=lower,
                insufficient_alone=(lower[keys[0]] >= .1 or lower[keys[1]] >= 1e-6))


def analyse_sample(state, reference):
    # decimal_relative deliberately relies on its caller's high precision.
    # Preserve exact float differences before constructing either diagnostic.
    with localcontext() as context:
        context.prec = 110
        relative = decimal_relative(state)
        return (differences((relative[:3],relative[3:]), reference),
                position_projection(relative,reference))


def load_evidence(path):
    path = Path(path).resolve()
    report = json.loads(path.read_text(encoding='utf-8'))
    if (report.get('complete') is not True or report.get('source_unchanged') is not True
            or report.get('checks_passed') is not False
            or report.get('production_eligible') is not False):
        raise ValueError('Expected the complete, preserved335 FAIL receipt')
    for name, sha in report['source_sha256'].items():
        if digest(ROOT/name) != sha:
            raise ValueError('Changed335 source: '+name)
    archive = (ROOT/report['sample_archive']).resolve()
    if not archive.is_relative_to(ROOT.resolve()) or digest(archive) != report['npz_sha256']:
        raise ValueError('Changed335 sample archive')
    with np.load(archive, allow_pickle=False) as data:
        arrays = {k: data[k].copy() for k in data.files}
    return report, arrays, dict(report_sha256=digest(path), npz_sha256=digest(archive))


def run(output):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('Preserve previous diagnosis')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh project .tools output')
    evidence, arrays, input_hashes = load_evidence(ROOT/EVIDENCE)
    fingerprints = sources()
    for name in (PROTOCOL, 'scripts/diagnose_rust_adaptive.py'):
        fingerprints[name] = digest(ROOT/name)
    snapshot = provenance(output.parent/(output.stem+'-sources'))
    report = dict(protocol=PROTOCOL, complete=False, runtime_modified=False,
        reintegration_performed=False, production_eligible=False,
        source_sha256=fingerprints, provenance=snapshot, input=input_hashes,
        environment=dict(python=platform.python_version(), numpy=np.__version__), results={})
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    start = perf_counter()
    save()
    try:
        cases = [('holdout_'+n, *holdout_fixture(e, a, p)) for n,e,a,p in CASES]
        cases += [('original_'+str(e), *fixture(e)) for e in (0., .5, .95)]
        if set(evidence['results']) != {name for name, _, _ in cases}:
            raise ValueError('Changed335 case set')
        for name, seed, times in cases:
            row = evidence['results'][name]
            initial = states(seed.bodies)
            request = row['input_request']
            if (not np.array_equal(times, arrays[name+'_times']) or request['times'] != times.tolist()
                    or request['masses'] != [b.mass for b in seed.bodies]
                    or np.asarray(request['states'],dtype='>f8').tobytes() != initial.astype('>f8').tobytes()):
                raise ValueError('Changed335 initial data or epochs: '+name)
            values = arrays[name+'_rust']
            if (values.shape != (len(times), *initial.shape) or not np.isfinite(values).all()
                    or values[0].astype('>f8').tobytes() != initial.astype('>f8').tobytes()):
                raise ValueError('Invalid335 trajectory: '+name)
            expected, sensitivities = references(seed, times)
            if np.asarray(expected,dtype='>f8').tobytes() != arrays[name+'_reference'].astype('>f8').tobytes():
                raise ValueError('Existing oracle export differs from335: '+name)
            errors, projections = [], []
            for time, value, reference in zip(times, values, expected):
                error, projection = analyse_sample(value, reference)
                errors.append(error)
                projections.append(dict(time_seconds=float(time), **projection))
            error = maximum(errors)
            if errors != row['rust']['sampled_errors'] or any(error[k] != row['rust'][k] for k in error):
                raise ValueError('Existing Decimal error metric differs from335: '+name)
            worst = max(range(len(errors)), key=lambda i: errors[i]['position_metres'])
            report['results'][name] = dict(original_gate_passed=row['rust']['checks_passed'],
                original_error=error, sensitivities=sensitivities,
                rounded_initial_relative=alternative_bound(error,sensitivities['rounded_initial_relative_effect']),
                rounded_native_gm=alternative_bound(error,sensitivities['rounded_native_gm_effect']),
                worst_position_projection=projections[worst], sampled_projections=projections)
            save()
            print(name, 'error',error['position_metres'], 'IC/GM bounds',
                  sensitivities['rounded_initial_relative_effect']['position_metres'],
                  sensitivities['rounded_native_gm_effect']['position_metres'],
                  'along',projections[worst]['along_fraction'], flush=True)
        if (any(digest(ROOT/n) != s for n,s in fingerprints.items())
                or digest(ROOT/EVIDENCE) != input_hashes['report_sha256']
                or digest(ROOT/evidence['sample_archive']) != input_hashes['npz_sha256']):
            raise ValueError('Inputs or sources changed during diagnosis')
        report.update(complete=True, source_unchanged=True, input_unchanged=True,
            original_passed_cases=sum(v['original_gate_passed'] for v in report['results'].values()),
            original_failed_cases=sum(not v['original_gate_passed'] for v in report['results'].values()),
            original_error_arrays_exactly_reproduced=True)
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        report['wall_seconds'] = perf_counter()-start
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
