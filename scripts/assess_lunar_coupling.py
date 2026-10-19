"""Offline snapshot audit: Newton rigid coupling and two lunar parameter sets.

No integration, ephemeris fit, physical PN mapping or runtime activation.
"""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from scipy.spatial.transform import Rotation

from scripts import de441_reader as de
from scripts.assess_de441_reader import qualification as reader_qualified
from scripts.assess_solar_defect import snapshot, relative_gap, statistics
from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.fixed_j2_year import inputs
from scripts.independent_lunar_coupling import derivatives
from scripts.newton_year import ROOT, hashes
from solar_simulator.nbody_rotation import correction
from solar_simulator.oblateness import earth_moon_quadrupoles, prepare, acceleration
from solar_simulator.orientation import lunar_rotation
from solar_simulator.native_forces import prepare as native_point
from solar_simulator.simulation import G
from solar_simulator.spin_initial import lunar_solid_equivalent_initial
from solar_simulator.storage import to_document

PROTOCOL = 'docs/lunar-coupling-protocol.md'
CHECKS = ('force', 'torque', 'potential', 'power', 'prescribed_bridge', 'linear', 'angular')
CONTROLS = ('missing_reaction', 'missing_torque', 'missing_spin_power')
CASES = ('earth_prescribed', 'nominal_moon', 'solid_moon')


def model_snapshot(seed):
    """Primitive deterministic state; Vector3 copies do not have value equality."""
    return json.dumps(to_document(seed), sort_keys=True, separators=(',', ':'), allow_nan=False)


def coefficients(figure, radius):
    """Unnormalised J2/C22; mean inertia is not inferred from these."""
    if not np.isfinite(radius) or radius <= 0:
        raise ValueError('Positive finite reference radius required')
    a, b, c = figure.moments
    scale = figure.mass*radius**2
    return (c-(a+b)/2)/scale, (b-a)/(4*scale)


def fraction(numerator, denominator):
    if not np.isfinite(numerator) or not np.isfinite(denominator) or numerator < 0 or denominator < 0:
        raise ValueError('Finite nonnegative defect and scale required')
    if denominator == 0:
        if numerator:
            raise ValueError('Nonzero defect against exact zero scale')
        return 0.
    return float(numerator/denominator)


def coupling_checks(positions, velocities, masses, source, figure, quaternion, matrix,
                    omega, relative_pair, prescribed_field):
    a, torque, energy = correction(positions, masses, source, figure, quaternion, relative_pair)
    targets = np.flatnonzero(np.arange(len(masses)) != source)
    r, v = positions[targets]-positions[source], velocities[targets]-velocities[source]
    first, second, rho = relative_pair
    if source in (first, second):
        target = second if source == first else first
        r[targets == target] = rho if source == first else -rho
    forces, reference_torque, reference_energy, rate = derivatives(
        r, v, masses[targets], figure.moments, matrix, omega, G)
    actual_forces = a[targets]*masses[targets, None]
    all_forces = a*masses[:, None]
    force_scale = float(np.linalg.norm(all_forces, axis=1).sum())
    orbital_torques = np.cross(r, actual_forces)
    torque_scale = float(np.linalg.norm(orbital_torques, axis=1).sum()+np.linalg.norm(torque))
    powers = np.sum(actual_forces*v, axis=1)
    spin_power = float(omega@torque)
    power_scale = float(np.abs(powers).sum()+abs(spin_power)+abs(rate))
    rows = dict(force=relative_gap(actual_forces, forces), torque=relative_gap(torque, reference_torque),
        potential=fraction(abs(energy-reference_energy), abs(reference_energy)),
        power=fraction(abs(float(powers.sum())+spin_power+rate), power_scale),
        prescribed_bridge=relative_gap(a, prescribed_field),
        linear=fraction(float(np.linalg.norm(all_forces.sum(axis=0))), force_scale),
        angular=fraction(float(np.linalg.norm(orbital_torques.sum(axis=0)+torque)), torque_scale))
    controls = dict(missing_reaction=fraction(float(np.linalg.norm(actual_forces.sum(axis=0))), force_scale),
        missing_torque=fraction(float(np.linalg.norm(orbital_torques.sum(axis=0))), torque_scale),
        missing_spin_power=fraction(abs(float(powers.sum())+rate), power_scale))
    return a, rows, controls


def qualification(rows, controls):
    if len(rows) != 440 or len(controls) != 440:
        return False
    if any(set(r) != set(CHECKS) for r in rows) or any(set(r) != set(CONTROLS) for r in controls):
        return False
    return bool(all(np.isfinite(r[k]) and 0 <= r[k] < (5e-12 if k in ('linear', 'angular') else 5e-10)
        for r in rows for k in CHECKS) and all(
        all(np.isfinite(r[k]) and r[k] >= 0 for r in controls) and max(r[k] for r in controls) > 1e-3
        for k in CONTROLS))


def run(output, reader_receipt):
    output = Path(output).resolve()
    if (not output.is_relative_to(ROOT/'.tools')
            or any(output.with_suffix(s).exists() for s in ('.json', '.npz'))):
        raise ValueError('Use fresh project .tools output; preserve failures')
    receipt = json.loads(Path(reader_receipt).read_bytes())
    if not receipt.get('complete') or not receipt.get('checks_passed') or not reader_qualified(receipt):
        raise ValueError('Require complete qualified reader evidence')
    for group in ('source_sha256', 'input_sha256'):
        if hashes(receipt[group]) != receipt[group]:
            raise ValueError('Changed reader source/input')
    seed, *_ = inputs()
    initial_metadata = model_snapshot(seed)
    reader, _ = de.load_archive(ROOT/de.ARCHIVE)
    figure, _, _, _ = lunar_solid_equivalent_initial()
    masses = np.array([b.mass for b in seed.bodies])
    if tuple(b.name for b in seed.bodies) != de.NAMES or figure.mass != masses[4]:
        raise ValueError('Pinned Moon mass or body order differs')
    earth, moon = earth_moon_quadrupoles(seed.bodies, seed.origin)
    j2, c22 = coefficients(figure, moon.reference_radius)
    solid = replace(moon, coefficient=j2, c22=c22, provenance='solid-equivalent I; diagnostic only')
    groups = dict(sun_fixed=(seed.settings.figures[0],), earth_fixed=(seed.settings.figures[1],),
        earth_prescribed=(earth,), moon_prescribed=(moon,))
    point = native_point(masses)
    import solar_native.solar_native as extension
    sources = {str(Path(module.__file__).resolve().relative_to(ROOT)) for module in tuple(sys.modules.values())
        if getattr(module, '__file__', None) and str(module.__file__).endswith('.py')
        and Path(module.__file__).resolve().is_relative_to(ROOT)
        and Path(module.__file__).resolve().parts[len(ROOT.parts)] in ('scripts', 'src')}
    sources = hashes(sorted(sources | {PROTOCOL}))
    bindings = hashes([reader_receipt, de.ARCHIVE, Path(extension.__file__),
        *sorted((ROOT/'src/solar_simulator/data').glob('*.json'))])
    report = dict(complete=False, checks_passed=False, source_sha256=sources, input_sha256=bindings,
        protocol=PROTOCOL, units='SI', origin=asdict(seed.origin), settings=asdict(seed.settings),
        names=list(de.NAMES), masses_kg=masses.tolist(),
        coefficients=dict(reference_radius_m=moon.reference_radius, nominal_j2=moon.coefficient,
            nominal_c22=moon.c22, solid_j2=j2, solid_c22=c22, moments_kg_m2=list(figure.moments)),
        propagation_performed=False, parameters_fitted=False, runtime_modified=False, network_used=False,
        prescribed_orientation_is_external=True, physical_lunar_mapping_certified=False,
        full_year_noether_balances_verified=False, conservative_spin_forecast_qualified=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    times = epoch_grid()
    arrays = dict(times=times, expected=np.empty((440, 10, 3)), expected_relative=np.empty((440, 3)),
        solid_field=np.empty((440, 10, 3)), nominal_field=np.empty((440, 10, 3)))
    for name in CASES:
        arrays['model_'+name] = np.empty((440, 10, 3))
    rows, controls, old_bridges = [], [], []
    start = perf_counter()

    def save():
        output.with_suffix('.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf8')

    save()
    try:
        for i, time in enumerate(times):
            time = float(time)
            state, rho = reader.states(time), reader.relative(time)
            p, v = state[:, :3], state[:, 3:]
            matrix, derivative = lunar_rotation(time)
            q = np.roll(Rotation.from_matrix(matrix).as_quat(), 1)
            # Use the same represented orientation, but no runtime quaternion formula in the oracle.
            matrix = Rotation.from_quat(np.roll(q, -1)).as_matrix()
            omega = .5*np.cross(matrix.T, derivative.T).sum(axis=0)
            prescribed_field = acceleration(p, masses, prepare(seed.bodies, (solid,)), time,
                _pair_displacement=(3, 4, rho))
            field, checks, negatives = coupling_checks(p, v, masses, 4, figure, q, matrix,
                omega, (3, 4, rho), prescribed_field)
            parts, models, bridge = snapshot(reader, time, seed, point, groups)
            rows.append(checks); controls.append(negatives); old_bridges.append(bridge)
            arrays['expected'][i] = reader.vectors(time, 2)
            arrays['expected_relative'][i] = reader.relative(time, 2)
            arrays['solid_field'][i], arrays['nominal_field'][i] = field, parts['moon_prescribed']
            arrays['model_earth_prescribed'][i] = models['earth_orientation']
            arrays['model_nominal_moon'][i] = models['earth_orientation_plus_moon']
            arrays['model_solid_moon'][i] = models['earth_orientation']+field
        report['checks_maximum_relative'] = {k: max(r[k] for r in rows) for k in CHECKS}
        report['negative_controls_maximum'] = {k: max(r[k] for r in controls) for k in CONTROLS}
        report['samples'] = 440
        report['coupling_checks_passed'] = qualification(rows, controls)
        report['previous_force_bridges_passed'] = bool(all(r['eih'] < 3e-14 and all(
            r[k] < 5e-12 for k in groups) for r in old_bridges))
        arrays['checks'] = np.array([[r[k] for k in CHECKS] for r in rows])
        arrays['negative_controls'] = np.array([[r[k] for k in CONTROLS] for r in controls])
        report['models'] = {}
        for name in CASES:
            field = arrays['model_'+name]
            defect = field-arrays['expected']
            relative = field[:, 4]-field[:, 3]-arrays['expected_relative']
            arrays['defect_'+name], arrays['relative_defect_'+name] = defect, relative
            report['models'][name] = dict(bodies={b: statistics(defect[:, j], times) for j, b in enumerate(de.NAMES)},
                moon_relative=statistics(relative, times))
        difference = arrays['solid_field']-arrays['nominal_field']
        arrays['field_difference'] = difference
        report['moon_field_difference'] = dict(bodies={b: statistics(difference[:, j], times) for j, b in enumerate(de.NAMES)},
            moon_relative=statistics(difference[:, 4]-difference[:, 3], times))
        if hashes(sources) != sources or hashes(bindings) != bindings or model_snapshot(seed) != initial_metadata:
            raise ValueError('Frozen scientific sources, inputs or model changed')
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report.update(complete=True, npz_sha256=hashes([output.with_suffix('.npz')]).popitem()[1],
            checks_passed=bool(report['coupling_checks_passed'] and report['previous_force_bridges_passed']
                and set(report['models']) == set(CASES) and all(np.isfinite(a).all() for a in arrays.values())))
    except BaseException as error:
        report.update(complete=False, checks_passed=False, failure=dict(type=type(error).__name__, message=str(error)))
        raise
    finally:
        report['wall_seconds'] = perf_counter()-start
        save()
    print('Lunar coupling audit complete', report['complete'], 'checks passed', report['checks_passed'], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reader-receipt', type=Path, required=True)
    args = parser.parse_args()
    if not run(args.output, args.reader_receipt)['checks_passed']:
        raise RuntimeError('Lunar coupling checks failed; evidence preserved')


if __name__ == '__main__':
    main()
