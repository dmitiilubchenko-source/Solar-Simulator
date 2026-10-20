"""Paired cost/regression check for allocation-free Vector3.distance_to.

The explicit legacy control retains the pre-change algorithm. Both paths use
the same installed integrator, settings, bodies and output epochs. This is
neither an independent physics oracle nor a new accuracy qualification.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import struct
from time import perf_counter
from unittest.mock import patch

import numpy as np
import scipy

from solar_simulator.cli import report
from solar_simulator.experiment import advance, preset
from solar_simulator.solar_profiles import solar_sandbox
from solar_simulator.storage import to_document
from solar_simulator.time_control import advance_towards
from solar_simulator.vector3 import Vector3

ROOT = Path(__file__).resolve().parents[1]


def legacy_distance(self, other):
    """Frozen control: the original distance method, including validation."""
    dist = self.subtract(other)
    magni = dist.magnitude()
    return magni


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(',', ':')).encode('utf-8')


def check_pairs():
    generator = random.Random(331)
    pairs = [(Vector3(0., 0., 0.), Vector3(0., -0., 0.)),
             (Vector3(1e308, 0., 0.), Vector3(-1e308, 0., 0.)),
             (Vector3(1e-300, 2e-300, 3e-300), Vector3(-1e-300, 0., 0.))]
    for _ in range(10000):
        pairs.append(tuple(Vector3(*(generator.uniform(-1, 1)*10**generator.uniform(-300, 300)
                                     for _ in range(3))) for _ in range(2)))
    for first, second in pairs:
        def outcome(function):
            try:
                return 'float64', struct.pack('>d', function(first, second))
            except (ValueError, OverflowError) as error:
                return type(error).__name__, str(error)
        if outcome(legacy_distance) != outcome(Vector3.distance_to):
            raise AssertionError('Distance value or rejection contract changed')
    return len(pairs)


def fingerprints():
    paths = [ROOT/name for name in ('scripts/profile_distance.py',
        'src/solar_simulator/vector3.py', 'src/solar_simulator/simulation.py',
        'src/solar_simulator/cli.py', 'src/solar_simulator/accuracy.py',
        'src/solar_simulator/diagnostics.py', 'src/solar_simulator/relativity.py')]
    import solar_native
    paths += list(Path(solar_native.__file__).parent.glob('*.pyd'))
    paths += [Path(scipy.__file__).parent/'integrate/_ivp/rk.py']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def benchmark(repetitions):
    original = Vector3.distance_to
    newton = preset('solar-system-asteroids-catalog', backend='rust')
    newton = replace(newton, settings=replace(newton.settings, integrator='dop853'))
    cases = {'strict10': solar_sandbox(profile='strict', backend='rust'), 'newton354': newton}
    result = {}
    for label, seed in cases.items():
        final = advance(seed, 20)
        expected = canonical((to_document(final), report(final)))
        expected_report = canonical(report(final))
        row = dict(bodies=len(seed.bodies), initial_sha256=hashlib.sha256(canonical(to_document(seed))).hexdigest(),
                   final_and_report_sha256=hashlib.sha256(expected).hexdigest())
        for task in ('report', 'packet_with_report'):
            calls_per_sample = 30 if label == 'strict10' and task == 'report' else 1
            def execute():
                state = advance(seed, 20) if task == 'packet_with_report' else final
                return state, report(state)
            # Warmup and validation/serialization are outside timed sections.
            for implementation in (legacy_distance, original):
                with patch.object(Vector3, 'distance_to', implementation):
                    state, values = execute()
                assert canonical((to_document(state), values)) == expected
            samples = {'legacy': [], 'current': []}
            for index in range(repetitions):
                order = (('legacy', legacy_distance), ('current', original))
                if index % 2:
                    order = order[::-1]
                for name, implementation in order:
                    with patch.object(Vector3, 'distance_to', implementation):
                        start = perf_counter()
                        for _ in range(calls_per_sample):
                            state, values = execute()
                        elapsed = (perf_counter()-start)/calls_per_sample
                    if canonical(values) != expected_report or canonical((to_document(state), values)) != expected:
                        raise AssertionError('Trajectory/report changed')
                    samples[name].append(elapsed)
            before, after = (statistics.median(samples[name]) for name in ('legacy', 'current'))
            row[task] = dict(raw_seconds=samples, legacy_median_seconds=before,
                             current_median_seconds=after, reduction_percent=100*(1-after/before),
                             calls_per_sample=calls_per_sample, exact_final_and_report=True)
            # Separate attribution, outside every timer: a path with zero
            # distance calls is a noise control, not evidence of acceleration.
            calls = [0]
            def counted_distance(first, second):
                calls[0] += 1
                return original(first, second)
            with patch.object(Vector3, 'distance_to', counted_distance):
                execute()
            row[task]['distance_calls'] = calls[0]
            row[task]['timing_is_unaffected_control'] = calls[0] == 0
            print(label, task, before, after, row[task]['reduction_percent'], flush=True)
        result[label] = row
    return result


def compare_year():
    """Same strict nominal year/20-hour packets, without a new JPL claim."""
    implementations = (('legacy', legacy_distance), ('current', Vector3.distance_to))
    sequences, costs = {}, {}
    for label, implementation in implementations:
        state = solar_sandbox(profile='strict', backend='rust')
        target = 31557600.
        hashes = [hashlib.sha256(canonical(to_document(state))).hexdigest()]
        start = perf_counter()
        with patch.object(Vector3, 'distance_to', implementation):
            while state.time < target:
                state = advance_towards(state, target, 20)
                hashes.append(hashlib.sha256(canonical(to_document(state))).hexdigest())
        costs[label] = perf_counter()-start
        sequences[label] = hashes
    if sequences['legacy'] != sequences['current']:
        raise AssertionError('Annual states changed')
    return dict(frames=len(hashes), packets=len(hashes)-1, duration_seconds=target,
                exact_all_checkpoint_bytes=True, frame_sha256=hashes,
                one_run_seconds=costs, speed_claim=False, new_ephemeris_accuracy_claim=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=7)
    parser.add_argument('--annual', action='store_true', help='Compare all strict year checkpoints too')
    args = parser.parse_args(argv)
    if args.repetitions < 3:
        parser.error('At least three alternating pairs required')
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Preserve previous measurements')
    before = fingerprints()
    pair_count = check_pairs()
    cases = benchmark(args.repetitions)
    annual = compare_year() if args.annual else None
    if fingerprints() != before:
        raise RuntimeError('Measured sources changed during benchmark')
    receipt = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        repetitions=args.repetitions, alternating_order=True, warmup_excluded=True,
        serialization_excluded=True, compared_binary_pairs=pair_count, source_sha256=before,
        source_unchanged=True, cases=cases, annual_comparison=annual, new_physics_accuracy_claim=False,
        small_case_regression_gate_passed=all(cases['strict10'][task]['reduction_percent'] >= -10.
            for task in ('report', 'packet_with_report')),
        report_354_gate_passed=cases['newton354']['report']['reduction_percent'] >= 15.)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return 0 if receipt['report_354_gate_passed'] and receipt['small_case_regression_gate_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
