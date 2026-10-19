"""Real-c conditional amplitudes on a DE441 path, not a propagated error bound."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
import scipy
from scipy.spatial.transform import Rotation

from scripts import de441_reader as de
from scripts.assess_de441_reader import qualification as reader_qualified
from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.canonical_initial import SIUnits
from scripts.eih_year import force_terms
from scripts.fixed_j2_ias import figure_force
from scripts.decimal_real_response import scalar_responses
from scripts.fixed_j2_year import inputs
from scripts.independent_real_spin import derivatives as reference_spin
from scripts.newton_year import ROOT, hashes, YEAR
from scripts.real_spin_scales import mixed_responses, spin_orbit, spin_identities, relative, vector_relative, hat
from solar_simulator.nbody_rotation import correction
from solar_simulator.oblateness import prepare, acceleration
from solar_simulator.orientation import lunar_rotation
from solar_simulator.relativity import C
from solar_simulator.simulation import G, AU
from solar_simulator.spin_initial import lunar_solid_equivalent_initial, from_rotation_rate

PROTOCOL = 'docs/real-spin-scales-protocol.md'
INDICES = (0, 1, 2, 13, 55, 110, 220, 330, 438, 439)
MIXED = ('pn2', 'moon_pnq', 'fixed_pnq')
ACCELERATIONS = tuple(name+'_'+suffix for name in MIXED for suffix in ('first', 'finite'))+(
    'moon_newton_q', 'so_force_over_mass', 'so_transport', 'so_q_torque_transport',
    'so_acceleration', 'so_acceleration_with_q_torque', 'so_orientation_q_delta_year')
VELOCITIES = ('so_velocity_shift',)


def statistics(values, times, unit, proxy=None):
    values = np.asarray(values)
    if values.shape != (len(times), 3) or not np.isfinite(values).all():
        raise ValueError('Finite vector series required')
    norms = np.linalg.norm(values, axis=1)
    row = dict(unit=unit, maximum=float(norms.max()), rms=float(np.sqrt(np.mean(norms**2))),
        initial=float(norms[0]), final=float(norms[-1]), worst_seconds=float(times[np.argmax(norms)]))
    if proxy not in (None, 'acceleration', 'velocity'):
        raise ValueError('Unknown proxy kind')
    if proxy:
        factor = YEAR*YEAR/2 if proxy == 'acceleration' else YEAR
        row['ballistic_proxy_m'] = factor*float(norms.max())
        row['ballistic_proxy_is_error_bound'] = False
    return row


def field_statistics(values, times, names, unit, proxy):
    if values.shape != (440, 10, 3) or tuple(names) != de.NAMES:
        raise ValueError('All 440 epochs and ten named bodies are required')
    return dict(bodies={name:statistics(values[:, i], times, unit, proxy) for i, name in enumerate(names)},
        moon_relative=statistics(values[:, 4]-values[:, 3], times, unit, proxy))


def snapshot(reader, seconds, masses, figure, prepared, units):
    state = reader.states(seconds); p = state[:, :3]-state[4, :3]; p[3] = -reader.relative(seconds)
    v = state[:, 3:]; r, dr = lunar_rotation(seconds)
    spin_state = from_rotation_rate(figure, r, dr)
    q, spin = np.asarray(spin_state.quaternion), np.asarray(spin_state.angular_momentum)
    r = Rotation.from_quat(q[[1, 2, 3, 0]]).as_matrix()
    aq, torque, _ = correction(p, masses, 4, figure, q)
    fixed = acceleration(p, masses, prepared, seconds)
    _, pn = force_terms(p, v, G*masses, C)
    components = dict(pn2=pn, moon_pnq=aq, fixed_pnq=fixed)
    mixed, diagnostics = mixed_responses(p, v, masses, components, units)
    independent_h = scalar_responses(p, v, masses, components, G, C)
    h_bridges = {name:vector_relative(pair[0]-independent_h[name], pair[0])
        for name, pair in mixed.items()}
    so = spin_orbit(p, v, masses, spin, 4, spin_rate=torque)
    oracle = reference_spin(p, v, masses, spin, 4, G, C)
    so_bridges = {name:vector_relative(so[name]-oracle[name], oracle[name]) for name in oracle}
    identities = spin_identities(p, v, masses, spin, 4, so)
    tensor = r@figure.quadrupole@r.T
    dq = YEAR*(hat(so['omega'])@tensor-tensor@hat(so['omega']))
    orientation = figure_force(p, masses, ((4, figure.bounding_radius, dq),))
    arrays = {name+'_'+suffix:pair[i] for name, pair in mixed.items() for i, suffix in enumerate(('first', 'finite'))}
    arrays.update(moon_newton_q=aq, so_force_over_mass=so['force']/masses[:, None],
        so_transport=so['material_transport'], so_q_torque_transport=so['q_torque_transport'],
        so_acceleration=so['acceleration'], so_acceleration_with_q_torque=so['acceleration_with_q_torque'],
        so_velocity_shift=so['velocity_shift'], so_orientation_q_delta_year=orientation)
    ds = r@(np.array(figure.moments)*(r.T@so['omega']))
    return arrays, dict(hessian=h_bridges, spin=so_bridges, identities=identities, matrix=diagnostics), dict(
        positions=p, velocities=v, spin=spin, spin_rate=torque, quaternion=q, omega=so['omega'],
        omega_by_source=so['omega_by_source'], initial_spin_shift=ds,
        initial_spin_shift_relative=float(np.linalg.norm(ds)/np.linalg.norm(spin)),
        material=so['material_transport']+so['q_torque_transport'], orientation=orientation)


def local_derivative_checks(data, masses, figure):
    x, v, spin, rate = (data[k] for k in ('positions', 'velocities', 'spin', 'spin_rate'))
    levels = []
    for h in (100., 10., 1.):
        plus = reference_spin(x+h*v, v, masses, spin+h*rate, 4, G, C)['velocity_shift']
        minus = reference_spin(x-h*v, v, masses, spin-h*rate, 4, G, C)['velocity_shift']
        finite = (plus-minus)/(2*h)
        levels.append(dict(h_seconds=h, relative=vector_relative(finite-data['material'], data['material'])))
    omega = data['omega']; size = np.linalg.norm(omega); rotations = []
    base = Rotation.from_quat(data['quaternion'][[1, 2, 3, 0]])
    for h in (1e-3, 1e-4):
        if size:
            fields = []
            for sign in (1, -1):
                q = np.roll((Rotation.from_rotvec(sign*h*omega/size)*base).as_quat(), 1)
                fields.append(correction(x, masses, 4, figure, q)[0])
            derivative = (fields[0]-fields[1])/(2*h)*size*YEAR
        else:
            derivative = np.zeros_like(x)
        rotations.append(dict(h_radians=h, relative=vector_relative(derivative-data['orientation'], data['orientation'])))
    return dict(material=levels, orientation=rotations,
        checks_passed=bool(levels[-1]['relative'] < 1e-6 and rotations[-1]['relative'] < 1e-6))


def qualification(report):
    if (not report.get('complete') or report.get('samples') != 440
            or set(report.get('fields', {})) != set(ACCELERATIONS+VELOCITIES)
            or len(report.get('bridges', [])) != 440
            or [r.get('index') for r in report.get('derivatives', [])] != list(INDICES)):
        return False
    for name, field in report['fields'].items():
        if set(field.get('bodies', {})) != set(de.NAMES) or 'moon_relative' not in field:
            return False
        for row in [*field['bodies'].values(), field['moon_relative']]:
            if (row.get('unit') != ('m/s' if name in VELOCITIES else 'm/s2')
                    or row.get('ballistic_proxy_is_error_bound') is not False
                    or any(k not in row or not np.isfinite(row[k]) or row[k] < 0
                        for k in ('maximum', 'rms', 'initial', 'final', 'worst_seconds', 'ballistic_proxy_m'))):
                return False
    rows = report['bridges']
    return bool(all(set(r['hessian']) == set(MIXED) and all(v < 5e-12 for v in r['hessian'].values())
        and set(r['spin']) == {'force', 'velocity_shift', 'omega'} and all(v < 5e-11 for v in r['spin'].values())
        and r['identities']['linear'] < 5e-12 and r['identities']['angular'] < 5e-12
        and r['matrix']['minimum_eigenvalue'] > 0 and set(r['matrix']['solve_relative']) == set(MIXED)
        and 'block_precision50_to70_relative' in r['matrix'] and r['matrix']['block_precision50_to70_relative'] < 1e-30
        and all(v < 5e-13 for v in r['matrix']['solve_relative'].values())
        for r in rows) and all(r['checks_passed'] for r in report['derivatives'])
        and max(r['identities']['missing_velocity'] for r in rows) > 1e-3
        and max(r['identities']['missing_source_reaction'] for r in rows) > 1e-3)


def run(output, reader_receipt):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or any(output.with_suffix(s).exists() for s in ('.json', '.npz')):
        raise ValueError('Use fresh project .tools output; preserve failures')
    receipt = json.loads(Path(reader_receipt).read_bytes())
    if not receipt.get('complete') or not receipt.get('checks_passed') or not reader_qualified(receipt):
        raise ValueError('Require complete qualified reader')
    for group in ('source_sha256', 'input_sha256'):
        if hashes(receipt[group]) != receipt[group]:
            raise ValueError('Reader source/input changed')
    seed, *_ = inputs(); masses = np.array([b.mass for b in seed.bodies])
    figure, _, _, _ = lunar_solid_equivalent_initial()
    if tuple(b.name for b in seed.bodies) != de.NAMES or figure.mass != masses[4]:
        raise ValueError('Pinned ten-body masses/order differ')
    reader, _ = de.load_archive(ROOT/de.ARCHIVE)
    prepared = prepare(seed.bodies, seed.settings.figures)
    units = SIUnits(float(masses[0]), AU, G); times = epoch_grid()
    sources = {str(Path(m.__file__).resolve().relative_to(ROOT)) for m in tuple(sys.modules.values())
        if getattr(m, '__file__', None) and str(m.__file__).endswith('.py')
        and Path(m.__file__).resolve().is_relative_to(ROOT)
        and Path(m.__file__).resolve().parts[len(ROOT.parts)] in ('scripts', 'src')}
    source_sha = hashes(sorted(sources | {PROTOCOL}))
    input_sha = hashes([reader_receipt, de.ARCHIVE, *sorted((ROOT/'src/solar_simulator/data').glob('*.json'))])
    report = dict(complete=False, checks_passed=False, source_sha256=source_sha, input_sha256=input_sha,
        protocol=PROTOCOL, origin=asdict(seed.origin), masses_kg=masses.tolist(), names=list(de.NAMES),
        c_m_per_s=C, G_SI=G, units=asdict(units), numpy=np.__version__, scipy=scipy.__version__,
        python=sys.version, runtime_modified=False, propagation_performed=False, parameters_fitted=False,
        physical_lunar_mapping_certified=False, annual_error_bound_certified=False,
        conservative_spin_forecast_qualified=False, spin_added_to_global_Rdot=False,
        real_one_km_accuracy_certified_from_proxies=False, network_used_during_audit=False,
        primary_SO_source=dict(url='https://arxiv.org/pdf/1011.1179v3', equation=66,
            sha256='b5daf350e62aa3c95a32ac7ccf9cfb8cf4f7d796f47978044756d1d99e96344e'),
        bridges=[], derivatives=[])
    arrays = dict(times=times, omega=np.empty((440, 3)), omega_by_source=np.empty((440, 10, 3)),
        spin_shift=np.empty((440, 3)), spin_shift_relative=np.empty(440))
    for name in ACCELERATIONS+VELOCITIES:
        arrays[name] = np.empty((440, 10, 3))
    start = perf_counter(); output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        output.with_suffix('.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf8')

    save()
    try:
        for i, t in enumerate(times):
            fields, checks, data = snapshot(reader, float(t), masses, figure, prepared, units)
            for name, field in fields.items(): arrays[name][i] = field
            for name in ('omega', 'omega_by_source'): arrays[name][i] = data[name]
            arrays['spin_shift'][i] = data['initial_spin_shift']; arrays['spin_shift_relative'][i] = data['initial_spin_shift_relative']
            report['bridges'].append(checks)
            if i in INDICES:
                report['derivatives'].append(dict(index=i, **local_derivative_checks(data, masses, figure)))
                save(); print('scales', i, 'derivatives', report['derivatives'][-1]['checks_passed'], flush=True)
        report['fields'] = {name:field_statistics(arrays[name], times, de.NAMES,
            'm/s2' if name in ACCELERATIONS else 'm/s', 'acceleration' if name in ACCELERATIONS else 'velocity')
            for name in ACCELERATIONS+VELOCITIES}
        omega = arrays['omega']
        report['spin'] = dict(omega=statistics(omega, times, 'rad/s'),
            omega_by_source={name:statistics(arrays['omega_by_source'][:, j], times, 'rad/s') for j, name in enumerate(de.NAMES)},
            maximum_rate_times_year_rad=float(np.linalg.norm(omega, axis=1).max()*YEAR),
            integral_vector_rad=np.trapezoid(omega, times, axis=0).tolist(),
            integral_norm_rad=float(np.trapezoid(np.linalg.norm(omega, axis=1), times)),
            initial_spin_shift_maximum_relative=float(arrays['spin_shift_relative'].max()))
        if hashes(source_sha) != source_sha or hashes(input_sha) != input_sha:
            raise ValueError('Frozen scientific source/input changed')
        if not all(np.isfinite(a).all() for a in arrays.values()):
            raise ValueError('Nonfinite scientific output')
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report.update(complete=True, samples=440, npz_sha256=hashes([output.with_suffix('.npz')]).popitem()[1])
        report['checks_passed'] = qualification(report)
    except BaseException as error:
        report.update(complete=False, checks_passed=False, failure=dict(type=type(error).__name__, message=str(error)))
        raise
    finally:
        report['wall_seconds'] = perf_counter()-start; save()
    print('Real SI amplitudes complete', report['complete'], 'checks passed', report['checks_passed'], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--reader-receipt', required=True, type=Path)
    args = parser.parse_args()
    if not run(args.output, args.reader_receipt)['checks_passed']:
        raise RuntimeError('Amplitude validation failed; evidence preserved')


if __name__ == '__main__':
    main()
