"""Instantaneous model defect on a prescribed DE441 path; never an orbit fit."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts import de441_reader as de
from scripts.assess_de441_reader import qualification as reader_qualified
from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.eih_year import force_terms
from scripts.fixed_j2_year import inputs
from scripts.independent_figure_vector import acceleration as vector_figure
from scripts.newton_year import ROOT, YEAR, hashes
from solar_simulator.native_forces import prepare as native_point
from solar_simulator.oblateness import prepare as prepare_figures, acceleration as tensor_figure, earth_moon_quadrupoles
from solar_simulator.relativity import C
from solar_simulator.simulation import G, AU

PROTOCOL = 'docs/solar-defect-protocol.md'
COMPONENTS = ('newton', 'pn', 'sun_fixed', 'earth_fixed', 'earth_prescribed', 'moon_prescribed')
CASES = ('newton', 'point_eih', 'strict', 'earth_orientation', 'earth_orientation_plus_moon')


def relative_gap(actual, expected):
    if actual.shape != expected.shape or not np.isfinite(actual).all() or not np.isfinite(expected).all():
        raise ValueError('Invalid force comparison arrays')
    scale = float(np.linalg.norm(expected, axis=-1).max())
    difference = float(np.linalg.norm(actual-expected, axis=-1).max())
    return difference/scale if scale else (0. if difference == 0. else float('inf'))


def compose(parts):
    if set(parts) != set(COMPONENTS):
        raise ValueError('Require all declared force components')
    point = parts['newton']+parts['pn']
    sun = point+parts['sun_fixed']
    return dict(newton=parts['newton'], point_eih=point, strict=sun+parts['earth_fixed'],
        earth_orientation=sun+parts['earth_prescribed'],
        earth_orientation_plus_moon=sun+parts['earth_prescribed']+parts['moon_prescribed'])


def statistics(values, times):
    if values.shape != (len(times), 3) or not np.isfinite(values).all():
        raise ValueError('Require finite vector series')
    norms = np.linalg.norm(values, axis=1)
    return dict(maximum_m_per_s2=float(norms.max()), rms_m_per_s2=float(np.sqrt(np.mean(norms**2))),
        initial_m_per_s2=float(norms[0]), final_m_per_s2=float(norms[-1]),
        worst_seconds=float(times[np.argmax(norms)]))


def snapshot(reader, seconds, seed, point, figure_groups):
    q = reader.states(seconds)
    rho = reader.relative(seconds)
    pair = (3, 4, rho)
    p, v = q[:, :3], q[:, 3:]
    masses = np.array([body.mass for body in seed.bodies])
    n = point(p, v, relative_pair=pair)
    full = point(p, v, C, pair)
    reference_n, reference_pn = force_terms(p, v, G*masses, C, pair)
    bridges = {'eih': relative_gap(full, reference_n+reference_pn)}
    parts = dict(newton=n, pn=full-n)
    for name, figures in figure_groups.items():
        parts[name] = tensor_figure(p, masses, prepare_figures(seed.bodies, figures), seconds, _pair_displacement=pair)
        reference = vector_figure(p/AU, G*masses*YEAR**2/AU**3, figures, list(de.NAMES),
            seconds, (3, 4, rho/AU))*AU/YEAR**2
        bridges[name] = relative_gap(parts[name], reference)
    return parts, compose(parts), bridges


def source_derivative_jumps(reader):
    jumps = {}
    for slot in range(11):
        count = int(reader.layout[2, slot])
        span = 32*de.DAY/count
        maximum = 0.
        for record in range(len(reader.records)):
            for segment in range(count):
                nr, ns = (record, segment+1) if segment+1 < count else (record+1, 0)
                if nr == len(reader.records):
                    continue
                a = de.polynomial(reader.coefficients(record, slot, segment), 1., span, 2)
                b = de.polynomial(reader.coefficients(nr, slot, ns), -1., span, 2)
                maximum = max(maximum, float(np.linalg.norm(a-b)*1000))
        jumps[str(slot)] = maximum
    return jumps


def run(output, reader_receipt):
    output = Path(output).resolve()
    if (not output.is_relative_to(ROOT/'.tools')
            or any(output.with_suffix(s).exists() for s in ('.json', '.npz'))):
        raise ValueError('Use fresh project .tools output; preserve failure evidence')
    receipt = json.loads(Path(reader_receipt).read_bytes())
    if not receipt['complete'] or not receipt['checks_passed'] or not reader_qualified(receipt):
        raise ValueError('Require qualified complete offline reader')
    for group in ('source_sha256', 'input_sha256'):
        if hashes(receipt[group]) != receipt[group]:
            raise ValueError('Reader scientific sources or data changed')
    seed, *_ = inputs()
    initial_metadata = (asdict(seed.settings), asdict(seed.origin), [b.mass for b in seed.bodies])
    reader, _ = de.load_archive(ROOT/de.ARCHIVE)
    earth, moon = earth_moon_quadrupoles(seed.bodies, seed.origin)
    groups = dict(sun_fixed=(seed.settings.figures[0],), earth_fixed=(seed.settings.figures[1],),
        earth_prescribed=(earth,), moon_prescribed=(moon,))
    point = native_point([b.mass for b in seed.bodies])
    import solar_native.solar_native as extension
    bindings = hashes([reader_receipt, de.ARCHIVE, Path(extension.__file__)])
    sources = hashes([PROTOCOL, 'scripts/assess_solar_defect.py', 'scripts/de441_reader.py',
        'scripts/eih_year.py', 'scripts/independent_figure_vector.py',
        *('src/solar_simulator/'+f for f in ('native_forces.py', 'oblateness.py', 'orientation.py', 'relativity.py')),
        *('src/solar_simulator/data/'+f for f in ('orientation-de441-20261008.json', 'earth-j2-20261008.json', 'solar-j2-20261008.json'))])
    times = epoch_grid()
    arrays = dict(times=times, expected=np.array([reader.vectors(float(t), 2) for t in times]),
        expected_relative=np.array([reader.relative(float(t), 2) for t in times]))
    for name in COMPONENTS: arrays['component_'+name] = np.empty((440, 10, 3))
    for name in CASES: arrays['model_'+name] = np.empty((440, 10, 3))
    report = dict(complete=False, checks_passed=False, protocol=PROTOCOL,
        source_sha256=sources, input_sha256=bindings, settings=asdict(seed.settings), origin=asdict(seed.origin),
        masses_kg=[b.mass for b in seed.bodies], names=list(de.NAMES), units='SI',
        network_used=False, propagation_performed=False, runtime_modified=False,
        parameters_fitted=False, prescribed_orientation_is_external=True,
        proven_cause_of_annual_orbit_residual=False, full_year_noether_balances_verified=False)
    start = perf_counter()
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        output.with_suffix('.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')

    save()
    try:
        bridges = []
        for i, t in enumerate(times):
            parts, models, checks = snapshot(reader, float(t), seed, point, groups)
            for name, a in parts.items(): arrays['component_'+name][i] = a
            for name, a in models.items(): arrays['model_'+name][i] = a
            bridges.append(checks)
        report['bridge_maximum_relative'] = {name: max(r[name] for r in bridges) for name in bridges[0]}
        report['bridge_all_epochs_passed'] = all(r['eih'] < 3e-14 and all(
            r[name] < 5e-12 for name in groups) for r in bridges)
        report['models'] = {}
        for name in CASES:
            model = arrays['model_'+name]
            delta = model-arrays['expected']
            relative = model[:, 4]-model[:, 3]-arrays['expected_relative']
            arrays['defect_'+name] = delta
            arrays['relative_defect_'+name] = relative
            report['models'][name] = dict(bodies={body:statistics(delta[:, i], times) for i, body in enumerate(de.NAMES)},
                moon_relative=statistics(relative, times))
        report['components'] = {name:dict(bodies={body:statistics(arrays['component_'+name][:, i], times)
                for i, body in enumerate(de.NAMES)}, moon_relative=statistics(
                    arrays['component_'+name][:, 4]-arrays['component_'+name][:, 3], times)) for name in COMPONENTS}
        report['source_acceleration_boundary_jumps_m_per_s2'] = source_derivative_jumps(reader)
        if (hashes(sources) != sources or hashes(bindings) != bindings
                or initial_metadata != (asdict(seed.settings), asdict(seed.origin), [b.mass for b in seed.bodies])):
            raise ValueError('Frozen source/inputs/actual dependency/model changed')
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report.update(npz_sha256=hashes([output.with_suffix('.npz')]).popitem()[1], complete=True,
            checks_passed=bool(report['bridge_all_epochs_passed'] and all(np.isfinite(a).all() for a in arrays.values())
                and set(report['models']) == set(CASES) and set(report['components']) == set(COMPONENTS)))
    except BaseException as error:
        report.update(complete=False, checks_passed=False, failure=dict(type=type(error).__name__, message=str(error)))
        raise
    finally:
        report['wall_seconds'] = perf_counter()-start
        save()
    print('Local defect complete', report['complete'], 'bridges passed', report['checks_passed'], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reader-receipt', type=Path, required=True)
    args = parser.parse_args()
    if not run(args.output, args.reader_receipt)['checks_passed']:
        raise RuntimeError('Force bridges failed; scientific evidence retained')


if __name__ == '__main__':
    main()
