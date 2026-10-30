"""Observe immutable candidate's unchanged375 driver; no force/solver replacement."""
import argparse
from contextlib import contextmanager
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys

TOOL_ROOT = Path(__file__).resolve().parents[1]


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def freeze_check(candidate, freeze, protocol):
    module = module_at('_freeze384', TOOL_ROOT/'scripts/qualify_newton384.py')
    return module.verify_freeze(candidate, freeze, protocol)


@contextmanager
def observe(folder):
    """Journal every completed runtime call; never modify returned states/arrays."""
    import numpy as np
    from scripts import qualify_current_runtime375 as driver
    from solar_simulator import accuracy, time_control
    from solar_simulator.error_control import PerBodyDOP853
    from solar_simulator.storage import to_document
    from scripts.assess_sandbox_planets import states
    original_propagate, original_advance = driver.propagate, time_control.advance_towards
    original_solve, original_load = accuracy.solve_ivp, np.load
    active = [None]
    rows = {}
    with (folder/'packets.jsonl').open('x', encoding='utf8', newline='\n') as journal:
        def emit(row):
            journal.write(json.dumps(row, allow_nan=False, separators=(',', ':'))+'\n')
            journal.flush()
        def propagate(times, backend, rtol, packet, label, job_folder, arrays, resume=False):
            if label in rows:
                raise ValueError('Repeated acquisition label')
            active[0] = label
            rows[label] = dict(solver_calls=0, nfev=0, packets=0, rtol=rtol,
                               internal_accepted_rejected_steps_known=False)
            seed = driver.strict_seed(backend)
            seed = replace(seed, settings=replace(seed.settings, rtol=rtol))
            emit(dict(job=label, kind='initial', document=to_document(seed), rtol=rtol))
            try:
                return original_propagate(times, backend, rtol, packet, label, job_folder, arrays, resume)
            finally:
                active[0] = None
        def advance(state, *args, **kwargs):
            result = original_advance(state, *args, **kwargs)
            label = active[0] or 'sandbox'
            if active[0]:
                rows[label]['packets'] += 1
            emit(dict(job=label, kind='completed_packet', start=state.time, end=result.time,
                      values=states(result.bodies).tolist()))
            return result
        def solve(*args, **kwargs):
            if kwargs.get('method') is not PerBodyDOP853 or kwargs.get('max_step', float('inf')) != float('inf'):
                raise ValueError('Expected actual production PerBodyDOP853 without max_step')
            if active[0]:
                if kwargs['rtol'] != rows[active[0]]['rtol']:
                    raise ValueError('Actual production tolerance changed')
                atol = np.asarray(kwargs['atol'])
                if atol.shape != (60,) or not np.array_equal(atol, np.r_[np.full(30, .001), np.full(30, 1e-9)]):
                    raise ValueError('Actual annual absolute tolerances/layout changed')
            result = original_solve(*args, **kwargs)
            if active[0]:
                rows[active[0]]['solver_calls'] += 1
                rows[active[0]]['nfev'] += int(result.nfev)
            return result
        def load(path, *args, **kwargs):
            if isinstance(path, (str, Path)) and not Path(path).resolve().is_relative_to(folder.resolve()):
                raise ValueError('Historical scientific arrays cannot replace acquisition')
            return original_load(path, *args, **kwargs)
        driver.propagate, time_control.advance_towards = propagate, advance
        accuracy.solve_ivp, np.load = solve, load
        try:
            yield rows
        finally:
            driver.propagate, time_control.advance_towards = original_propagate, original_advance
            accuracy.solve_ivp, np.load = original_solve, original_load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', choices=('current', 'reference'))
    for name in ('candidate', 'freeze', 'protocol', 'work'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    sys.path[:0] = [str(args.candidate/'src'), str(args.candidate)]
    from scripts import qualify_current_runtime375 as driver
    if driver.ROOT.resolve() != args.candidate.resolve():
        raise ValueError('Driver must come from unchanged candidate checkout')
    frozen = freeze_check(args.candidate, args.freeze, args.protocol)
    driver.verify_inputs(driver.protocol(args.protocol, frozen['protocol_SHA256']))
    options = dict(work=args.work, protocol_path=args.protocol, expected_sha=frozen['protocol_SHA256'])
    trace = args.work/(args.job+'-trace.json')
    if trace.exists() or (args.work/('run-'+args.job)).exists():
        raise FileExistsError('Preserve complete or partial annual output')
    rows, failure, unchanged = {}, None, False
    try:
        if args.job == 'current':
            with observe(args.work) as rows:
                driver.runtime_job('current', **options)
            if len(rows) != 8 or any(r['nfev'] <= 0 for r in rows.values()):
                raise ValueError('Missing annual/holdout production solves')
        else:
            driver.reference_job(**options)
    except BaseException as error:
        failure = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        try:
            freeze_check(args.candidate, args.freeze, args.protocol)
            unchanged = True
        finally:
            driver.write_json(trace, dict(job=args.job, rows=rows, failure=failure,
                complete=failure is None and unchanged, source_environment_unchanged=unchanged,
                freeze_SHA256=driver.sha(args.freeze), protocol_SHA256=frozen['protocol_SHA256']))


if __name__ == '__main__':
    main()
