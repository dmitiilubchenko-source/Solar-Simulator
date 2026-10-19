"""Qualify the offline reader with frozen Horizons data and independent arithmetic."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts import de441_reader as de
from scripts import de441_decimal as high
from scripts.assess_nominal_jpl import (load_archive as jpl_archive, validate_data, validate_probe,
    ARCHIVE as JPL_ARCHIVE)
from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.fixed_j2_year import inputs
from scripts.newton_year import ROOT, hashes

PROTOCOL = 'docs/de441-reader-protocol.md'
INDICES = (0, 1, 2, 13, 55, 110, 220, 330, 438, 439)


def errors(actual, expected):
    delta = np.linalg.norm(actual-expected, axis=-1)
    return float(delta.max()), int(np.argmax(delta))


def jpl_metrics(actual, relative, expected, times):
    rows = {}
    for index, name in enumerate(de.NAMES):
        p, worst = errors(actual[:, index, :3], expected[:, index, :3])
        v, _ = errors(actual[:, index, 3:], expected[:, index, 3:])
        rows[name] = dict(position_metres=p, velocity_m_per_s=v, worst_seconds=float(times[worst]),
            strict_passed=bool(p < .01 and v < 1e-8), timing_budget_passed=bool(p < 10.01 and v < 1e-5))
    pair = expected[:, 4]-expected[:, 3]
    p, worst = errors(relative[:, :3], pair[:, :3])
    v, _ = errors(relative[:, 3:], pair[:, 3:])
    return dict(bodies=rows, moon_relative=dict(position_metres=p, velocity_m_per_s=v,
        worst_seconds=float(times[worst]), strict_passed=bool(p < .001 and v < 1e-8),
        timing_budget_passed=bool(p < .201 and v < 1e-5)))


def boundaries(reader):
    maxima = np.zeros(3)
    worst = [None]*3
    count = 0
    for slot in range(11):
        parts = int(reader.layout[2, slot])
        span = 32*de.DAY/parts
        for record in range(len(reader.records)):
            for segment in range(parts):
                right_record, right_segment = (record, segment+1) if segment+1 < parts else (record+1, 0)
                if right_record >= len(reader.records):
                    continue
                a = reader.coefficients(record, slot, segment)
                b = reader.coefficients(right_record, slot, right_segment)
                for order in range(3):
                    delta = float(np.linalg.norm(de.polynomial(a, 1., span, order)-de.polynomial(b, -1., span, order))*1000)
                    if delta > maxima[order]:
                        maxima[order] = delta
                        worst[order] = dict(slot=slot, record=record, segment=segment)
                count += 1
    return dict(boundary_pairs=count, maximum_by_order_si=maxima.tolist(), worst=worst,
        checks_passed=bool(np.all(maxima < [.01, 1e-7, 1e-9])))


def decimal_check(reader, times):
    rows = []
    for index in INDICES:
        second = float(times[index])
        a, pair_a = high.snapshot(reader, second, 70)
        b, pair_b = high.snapshot(reader, second, 90)
        actual = np.array([reader.vectors(second, order) for order in range(3)])
        relative = np.array([reader.relative(second, order) for order in range(3)])
        error = high.difference(actual, b).max(axis=1)
        pair_error = high.difference(relative, pair_b)
        precision = max(high.agreement(a, b), high.agreement(pair_a, pair_b))
        rows.append(dict(index=index, seconds=second, body_error_by_order_si=error.tolist(),
            pair_error_by_order_si=pair_error.tolist(), precision_scaled_difference=precision,
            checks_passed=bool(np.all(error < [.01, 1e-8, 1e-12])
                and np.all(pair_error < [.001, 1e-8, 1e-12]) and precision < 1e-50)))
    return dict(rows=rows, checks_passed=all(r['checks_passed'] for r in rows))


def finite_differences(reader, times):
    rows = []
    for index in INDICES:
        second = float(times[index])
        if second < 1000. or second+1000 > reader.duration:
            continue
        q = np.array([reader.vectors(second, order) for order in range(3)])
        relative = np.array([reader.relative(second, order) for order in range(3)])
        levels = []
        for h in (1000., 100., 10.):
            derivatives = [(reader.vectors(second+h, o)-reader.vectors(second-h, o))/(2*h) for o in (0, 1)]
            pair_derivatives = [(reader.relative(second+h, o)-reader.relative(second-h, o))/(2*h) for o in (0, 1)]
            body_errors = [np.linalg.norm(v-q[o+1], axis=1)/np.maximum(np.linalg.norm(q[o+1], axis=1), 1e-12)
                for o, v in enumerate(derivatives)]
            pair_errors = [float(np.linalg.norm(v-relative[o+1])/max(np.linalg.norm(relative[o+1]), 1e-12))
                for o, v in enumerate(pair_derivatives)]
            levels.append(dict(h_seconds=h, body_relative_error_by_derivative=np.array(body_errors).tolist(),
                pair_relative_error_by_derivative=pair_errors))
        last = levels[-1]
        rows.append(dict(index=index, seconds=second, levels=levels, checks_passed=bool(
            np.all(np.max(last['body_relative_error_by_derivative'], axis=1) < [1e-6, 1e-5])
            and np.all(np.array(last['pair_relative_error_by_derivative']) < [1e-6, 1e-5]))))
    return dict(rows=rows, checks_passed=len(rows) == 9 and all(r['checks_passed'] for r in rows))


def negative_controls(reader, times, expected):
    rows = {}
    initial = reader.states(float(times[0]))
    raw = np.array([reader.component(slot, 0.) for slot in de.SLOTS])
    earth = raw[3]-raw[4]/(1+reader.constants['EMRAT'])
    raw[4] += earth
    raw[3] = earth
    controls = {'no_rotation': raw*1000, 'wrong_rotation_sign': raw @ reader.frame*1000}
    wrong_earth = initial[:, :3].copy()
    wrong_earth[3] = reader.frame @ reader.component(2, 0.)*1000
    controls['earth_is_emb'] = wrong_earth
    wrong_mass = initial[:, :3].copy()
    shift = reader.frame @ (reader.component(9, 0.)*(1/(1+reader.constants['EMRAT'])-1/(1+81.3)))*1000
    wrong_mass[3:5] += shift
    controls['rounded_emrat'] = wrong_mass
    for name, value in controls.items():
        p = float(np.linalg.norm(value-expected[0, :, :3], axis=1).max())
        rows[name] = dict(position_metres=p, detected=bool(p >= .01))
    v = float(np.linalg.norm(initial[:, 3:]*86400-expected[0, :, 3:], axis=1).max())
    rows['per_day_velocity'] = dict(velocity_m_per_s=v, detected=bool(v >= 1e-8))
    return dict(rows=rows, checks_passed=all(r['detected'] for r in rows.values()))


def qualification(report):
    if (set(report['jpl']['bodies']) != set(de.NAMES)
            or [r['index'] for r in report['decimal']['rows']] != list(INDICES)
            or report['boundaries']['boundary_pairs'] != 2749
            or len(report['finite_differences']['rows']) != 9):
        return False
    return bool(all(r['strict_passed'] for r in report['jpl']['bodies'].values())
        and report['jpl']['moon_relative']['strict_passed']
        and all(report[key]['checks_passed'] for key in ('decimal', 'boundaries', 'finite_differences', 'negative_controls')))


def run(output):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'.tools'):
        raise ValueError('Use fresh project .tools output; preserve failures')
    output.parent.mkdir(parents=True, exist_ok=True)
    sources = hashes([PROTOCOL, 'scripts/de441_reader.py', 'scripts/de441_decimal.py',
        'scripts/assess_de441_reader.py', 'tests/test_de441_reader.py', 'scripts/fetch_figure_profile.py'])
    bindings = hashes([de.ARCHIVE, JPL_ARCHIVE, 'docs/offline-sources-validation.json'])
    report = dict(complete=False, checks_passed=False, protocol=PROTOCOL,
        source_sha256=sources, input_sha256=bindings, network_used=False, propagation_performed=False,
        runtime_modified=False, initial_conditions_fitted=False, ten_year_simulator_accuracy_qualified=False)
    start = perf_counter()

    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')

    save()
    try:
        stamp = perf_counter()
        reader, metadata = de.load_archive(ROOT/de.ARCHIVE)
        report['reader_load_seconds'] = perf_counter()-stamp
        files = jpl_archive(ROOT/JPL_ARCHIVE)
        seed, prior, *_ = inputs()
        validate_probe(files)
        expected, timing = validate_data(files, seed, prior)
        times = epoch_grid()
        stamp = perf_counter()
        actual = np.array([reader.states(float(t)) for t in times])
        relative = np.array([np.r_[reader.relative(float(t)), reader.relative(float(t), 1)] for t in times])
        report['reader_440_states_seconds'] = perf_counter()-stamp
        report['jpl'] = jpl_metrics(actual, relative, expected, times)
        report['timing'] = timing
        report['metadata'] = metadata
        report['boundaries'] = boundaries(reader)
        save()
        report['decimal'] = decimal_check(reader, times)
        report['finite_differences'] = finite_differences(reader, times)
        report['negative_controls'] = negative_controls(reader, times, expected)
        roundtrip = (de.EPOCH+times/de.DAY-de.EPOCH)*de.DAY-times
        report['float_jd_roundtrip_max_seconds'] = float(np.abs(roundtrip).max())
        if hashes(sources) != sources or hashes(bindings) != bindings:
            raise ValueError('Frozen reader/data/protocol changed')
        report.update(complete=True, checks_passed=qualification(report))
        save()
    except BaseException as error:
        report.update(complete=False, checks_passed=False, failure=dict(type=type(error).__name__, message=str(error)))
        raise
    finally:
        report['wall_seconds'] = perf_counter()-start
        save()
    print('DE441 reader complete', report['complete'], 'passed', report['checks_passed'], 'seconds', report['wall_seconds'], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not run(args.output)['checks_passed']:
        raise RuntimeError('Reader protocol failed; complete evidence retained')


if __name__ == '__main__':
    main()
