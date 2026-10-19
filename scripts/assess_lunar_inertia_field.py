"""Offline inertia/field metrology on DE441 states; no propagation or fitting."""
import argparse
from decimal import Decimal, localcontext
from itertools import product
import json
from pathlib import Path
import sys
from time import perf_counter
from zipfile import ZipFile

import numpy as np
from scipy.spatial.transform import Rotation

from scripts import de441_reader as de
from scripts.assess_de441_reader import qualification as reader_qualified
from scripts.assess_lunar_coupling import model_snapshot
from scripts.assess_relativity import independent_acceleration
from scripts.assess_solar_defect import statistics
from scripts.eih_year import force_terms
from scripts.free_lunar_rotation import initial
from scripts.independent_figure_vector import acceleration as vector_field
from scripts.newton_year import ROOT, YEAR, hashes
from solar_simulator.nbody_rotation import correction
from solar_simulator.oblateness import acceleration, earth_moon_quadrupoles, prepare
from solar_simulator.orientation import lunar_rotation
from solar_simulator.rotation import RigidFigure
from solar_simulator.simulation import AU, G

PROTOCOL = 'docs/lunar-inertia-field-protocol.md'
TESTS = 'tests/test_lunar_inertia_field.py'
SOLID = 'src/solar_simulator/data/lunar-spin-solid-equivalent-20261008.json'
ORIENTATION = 'src/solar_simulator/data/orientation-de441-20261008.json'
PINS = {SOLID: '733d91c85c47f991fa7b39dcf66b61efcf62e0990ab74dbf7756af797a4081ba',
        ORIENTATION: 'e2919814946832a4b6635aa0643ce415ffc47fa34945d9c43b53dc61697695eb'}
TIMES = np.arange(1462, dtype=float)*21600.
PREFLIGHT = np.array([0, 730, 1461])
CASES = ('strict', 'solid_fixed', 'nominal_fixed', 'nominal_earth_prescribed')
BRIDGES = ('point', 'nominal_vector', 'completion_mean', 'completion_shifted')


def own_relative(actual, expected):
    """Per-body vector norms; an outer body's small field is never hidden."""
    actual, expected = np.asarray(actual), np.asarray(expected)
    if (actual.shape != expected.shape or actual.ndim != 2 or actual.shape[1] != 3
            or not np.isfinite(actual).all() or not np.isfinite(expected).all()):
        raise ValueError('Finite equally shaped per-body vectors required')
    error, scale = np.linalg.norm(actual-expected, axis=1), np.linalg.norm(expected, axis=1)
    if np.any((scale == 0) & (error != 0)):
        raise ValueError('Nonzero field against exact zero reference')
    return np.divide(error, scale, out=np.zeros_like(error), where=scale != 0)


def complete_moments(mean, j2, c22):
    """Normalized diagonal inertia; isotropic completion is not a spin model."""
    return mean-j2/3-2*c22, mean-j2/3+2*c22, mean+2*j2/3


def coefficients(moments):
    a, b, c = moments
    return c-(a+b)/2, (b-a)/4


def decimal_header(raw):
    """Read the pinned source tokens before float conversion."""
    text = raw.decode('ascii')
    names = text.split('GROUP   1040')[1].split('GROUP   1041')[0].split()
    values = text.split('GROUP   1041')[1].split('GROUP   1050')[0].split()
    if int(names[0]) != len(names)-1 or len(names) != len(values) or int(values[0]) != len(values)-1:
        raise ValueError('DE constant inventory differs')
    return dict(zip(names[1:], (Decimal(v.replace('D', 'E')) for v in values[1:])))


def arithmetic(header, solid, orientation):
    """Independent high precision inversion, conditional rounding, Park47-51."""
    with localcontext() as context:
        context.prec = 70
        d = Decimal
        h = d(str(solid['normalized_mean_solid_inertia']))
        offsets = tuple(d(str(v)) for v in solid['normalized_moment_offsets'])
        sj, sc = coefficients(offsets)
        j2, c22 = header['J2M'], header['C22M']
        nominal = orientation['figures']['Moon']
        if (nominal['j2'] != float(j2) or nominal['c22'] != float(c22)
                or nominal['radius_metres'] != float(header['AM']*1000)):
            raise ValueError('Orientation profile does not exactly match header J2/C22/AM')
        roundtrip = []
        for mean in (h, h*d('1.1')):
            moments = complete_moments(mean, j2, c22)
            dj, dc = coefficients(moments)
            fj, fc = coefficients(tuple(map(float, moments)))
            roundtrip.append(dict(mean=str(mean), normalized_moments=list(map(str, moments)),
                decimal_relative=[str(abs(dj/j2-1)), str(abs(dc/c22-1))],
                float_relative=[abs(fj/float(j2)-1), abs(fc/float(c22)-1)]))
        half = d('5e-9')
        corners = [coefficients(tuple(o+s*half for o, s in zip(offsets, signs)))
                   for signs in product((-1, 1), repeat=3)]
        bounds = [(min(c[k] for c in corners), max(c[k] for c in corners)) for k in (0, 1)]
        beta, gamma = header['LBET'], header['LGAM']
        denominator = 2*beta-gamma+beta*gamma
        park = (2*j2*(1-beta*gamma)/denominator, 2*j2*(1+gamma)/denominator,
                2*j2*(1+beta)/denominator)
        pj, pc = coefficients(park)
        return dict(solid_coefficients=dict(j2=str(sj), c22=str(sc)),
            nominal_coefficients=dict(j2=str(j2), c22=str(c22)), completions=roundtrip,
            nominal_minus_solid=dict(j2=str(j2-sj), c22=str(c22-sc)),
            rounding=dict(assumption='Independent nearest rounding of each offset to 1e-8; not covariance',
                vertices=8, bounds=[[str(a), str(b)] for a, b in bounds],
                nominal_inside=[lo <= v <= hi for v, (lo, hi) in zip((j2, c22), bounds)],
                mean_uncertainty_cancels=True),
            ratios=dict(solid_c22_over_j2=str(sc/sj), nominal_c22_over_j2=str(c22/j2),
                common_mass_radius_scaling_cannot_change_ratio=True),
            conditional_park=dict(assumption='Header J2M treated as undistorted J2 tilde; no I/S certification',
                normalized_moments=list(map(str, park)), j2_roundtrip=str(pj-j2),
                inferred_c22=str(pc), c22_minus_header=str(pc-c22),
                beta_roundtrip=str((park[2]-park[0])/park[1]-beta),
                gamma_roundtrip=str((park[1]-park[0])/park[2]-gamma)),
            physical_spin_mapping_certified=False)


def boundary_distance(reader, seconds):
    """Distance to the nearest Moon/slot9 polynomial boundary, in seconds."""
    _, _, x, span = reader.locate(9, float(seconds))
    return float(min(abs(x+1), abs(1-x))*span/2)


def snapshot(reader, seconds, model, seed, prepared, completions, moon):
    state, rho = reader.states(seconds), reader.relative(seconds)
    x, v = state[:, :3]/AU, state[:, 3:]/model.units.velocity_m_s
    pair = (3, 4, rho/AU)
    an, ap = force_terms(x, v, model.masses, model.c, pair)
    reference = independent_acceleration(x, v, model.masses, model.c, pair)
    unit = model.units.length_m/model.units.time_s**2
    parts = dict(point=(an+ap)*unit)
    centered = (x-x[4])*AU
    centered[3] = -rho
    masses = np.asarray(model.masses_si)
    for name, entries in prepared.items():
        parts[name] = acceleration(centered, masses, entries, seconds, _pair_displacement=(3, 4, rho))
    matrix, _ = lunar_rotation(seconds)
    quaternion = np.roll(Rotation.from_matrix(matrix).as_quat(), 1)
    parts['solid'], solid_torque, _ = correction(centered, masses, 4, model.figure, quaternion)
    vector = vector_field(centered/AU, G*masses*YEAR**2/AU**3, (moon,), list(de.NAMES),
                          seconds, pair)*AU/YEAR**2
    checks = [own_relative(an+ap, reference), own_relative(parts['moon'], vector)]
    torques = [solid_torque]
    for figure in completions:
        field, torque, _ = correction(centered, masses, 4, figure, quaternion)
        checks.append(own_relative(field, parts['moon']))
        torques.append(torque)
    base = parts['point']+parts['sun']
    models = dict(strict=base+parts['earth_fixed'],
        solid_fixed=base+parts['earth_fixed']+parts['solid'],
        nominal_fixed=base+parts['earth_fixed']+parts['moon'],
        nominal_earth_prescribed=base+parts['earth_prescribed']+parts['moon'])
    return parts, models, np.array(checks), np.array(torques)


def grouped_metrics(defect, relative, times, boundary):
    result = {}
    for name, mask in (('all', np.ones(len(times), dtype=bool)), ('boundary', boundary), ('interior', ~boundary)):
        result[name] = dict(samples=int(mask.sum()))
        if mask.any():
            result[name].update(bodies={b: statistics(defect[mask, i], times[mask]) for i, b in enumerate(de.NAMES)},
                                moon_relative=statistics(relative[mask], times[mask]))
    return result


def qualification(arrays, arithmetic_result, expected_times):
    """Derive success from full inventory and raw per-body bridges, not flags."""
    count = len(expected_times)
    shapes = dict(times=(count,), boundary_distance=(count,), expected=(count, 10, 3),
        expected_relative=(count, 3), checks=(count, 4, 10), torques=(count, 3, 3),
        boundary_jump=(count, 3), boundary_left=(count, 3), boundary_right=(count, 3))
    shapes.update({'part_'+k: (count, 10, 3) for k in ('point','sun','earth_fixed','earth_prescribed','moon','solid')})
    shapes.update({'model_'+k: (count, 10, 3) for k in CASES})
    shapes.update({'defect_'+k: (count, 10, 3) for k in CASES})
    shapes.update({'relative_defect_'+k: (count, 3) for k in CASES})
    if set(arrays) != set(shapes) or any(np.shape(arrays[k]) != shape or not np.isfinite(arrays[k]).all()
                                       for k, shape in shapes.items()):
        return False
    checks = arrays['checks']
    return bool(np.array_equal(arrays['times'], expected_times) and np.all(checks >= 0)
        and np.all(checks[:, 0] < 5e-12) and np.all(checks[:, 1:] < 5e-10)
        and np.all(arrays['boundary_distance'] >= 0)
        and all(max(c['float_relative']) < 5e-12
                and max(map(Decimal, c['decimal_relative'])) < Decimal('5e-12')
                for c in arithmetic_result['completions']))


def run(output, reader_receipt, preflight=False):
    output = Path(output).resolve()
    if (not output.is_relative_to(ROOT/'.tools')
            or any(output.with_suffix(s).exists() for s in ('.json', '.npz'))):
        raise ValueError('Use fresh project .tools output; preserve failures')
    receipt = json.loads(Path(reader_receipt).read_bytes())
    if not receipt.get('complete') or not receipt.get('checks_passed') or not reader_qualified(receipt):
        raise ValueError('Qualified complete DE441 reader required')
    for group in ('source_sha256', 'input_sha256'):
        if hashes(receipt[group]) != receipt[group]:
            raise ValueError('Reader source/input changed')
    if hashes(PINS) != PINS:
        raise ValueError('Lunar source profiles changed')
    model, _, seed = initial()
    before = model_snapshot(seed)
    if tuple(b.name for b in seed.bodies) != de.NAMES:
        raise ValueError('Pinned ten-body inventory required')
    reader, _ = de.load_archive(ROOT/de.ARCHIVE)
    with ZipFile(ROOT/de.ARCHIVE) as archive:
        header = decimal_header(archive.read('de441-header.txt'))
    solid, orientation = (json.loads((ROOT/p).read_bytes()) for p in (SOLID, ORIENTATION))
    numbers = arithmetic(header, solid, orientation)
    earth, moon = earth_moon_quadrupoles(seed.bodies, seed.origin)
    prepared = {name: prepare(seed.bodies, figures) for name, figures in dict(
        sun=seed.settings.figures[:1], earth_fixed=seed.settings.figures[1:],
        earth_prescribed=(earth,), moon=(moon,)).items()}
    completions = tuple(RigidFigure(model.figure.mass,
        tuple(float(v)*model.figure.mass*moon.reference_radius**2 for v in item['normalized_moments']),
        model.figure.bounding_radius) for item in numbers['completions'])
    sources = {str(Path(m.__file__).resolve().relative_to(ROOT)) for m in tuple(sys.modules.values())
        if getattr(m, '__file__', None) and str(m.__file__).endswith('.py')
        and Path(m.__file__).resolve().is_relative_to(ROOT)
        and Path(m.__file__).resolve().parts[len(ROOT.parts)] in ('scripts', 'src')}
    sources = hashes(sorted(sources | {PROTOCOL, TESTS}))
    inputs = hashes([reader_receipt, de.ARCHIVE, *sorted((ROOT/'src/solar_simulator/data').glob('*.json'))])
    times = TIMES[PREFLIGHT] if preflight else TIMES.copy()
    arrays = dict(times=times, boundary_distance=np.empty(len(times)), expected=np.empty((len(times),10,3)),
        expected_relative=np.empty((len(times),3)), checks=np.empty((len(times),4,10)),
        torques=np.empty((len(times),3,3)), boundary_jump=np.zeros((len(times),3)),
        boundary_left=np.zeros((len(times),3)), boundary_right=np.zeros((len(times),3)))
    report = dict(complete=False, checks_passed=False, preflight=bool(preflight), protocol=PROTOCOL,
        source_sha256=sources, input_sha256=inputs, arithmetic=numbers, samples=len(times),
        names=list(de.NAMES), units='SI', frame='Ecliptic J2000', center='SSB', epoch_jd_tdb=de.EPOCH,
        propagation_performed=False, runtime_modified=False, parameters_fitted=False, network_used=False,
        physical_lunar_mapping_certified=False, real_error_cause_attributed=False,
        source_seams_included_in_overall_statistics=True,
        earth_orientation_is_approximate=True, prescribed_orientation_is_external=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = perf_counter()

    def save():
        output.with_suffix('.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf8')

    save()
    try:
        for i, time in enumerate(times):
            time = float(time)
            parts, models, checks, torques = snapshot(reader, time, model, seed, prepared, completions, moon)
            arrays['expected'][i], arrays['expected_relative'][i] = reader.vectors(time, 2), reader.relative(time, 2)
            arrays['checks'][i], arrays['torques'][i] = checks, torques
            arrays['boundary_distance'][i] = boundary_distance(reader, time)
            if arrays['boundary_distance'][i] <= 1 and 0 < time < TIMES[-1]:
                arrays['boundary_left'][i] = reader.relative(time-.001, 2)
                arrays['boundary_right'][i] = reader.relative(time+.001, 2)
                arrays['boundary_jump'][i] = arrays['boundary_right'][i]-arrays['boundary_left'][i]
            for prefix, values in (('part_', parts), ('model_', models)):
                for name, value in values.items():
                    if prefix+name not in arrays:
                        arrays[prefix+name] = np.empty((len(times),10,3))
                    arrays[prefix+name][i] = value
        boundary = arrays['boundary_distance'] <= 1
        report['models'] = {}
        for name in CASES:
            field = arrays['model_'+name]
            defect = field-arrays['expected']
            relative = field[:,4]-field[:,3]-arrays['expected_relative']
            arrays['defect_'+name], arrays['relative_defect_'+name] = defect, relative
            report['models'][name] = grouped_metrics(defect, relative, times, boundary)
        report['checks_maximum_per_body'] = {name:dict(zip(de.NAMES, map(float, arrays['checks'][:,i].max(axis=0))))
                                            for i, name in enumerate(BRIDGES)}
        report['boundary'] = dict(samples=int(boundary.sum()), interior_samples=int((~boundary).sum()),
            jump_step_seconds=.001, maximum_relative_acceleration_jump_m_per_s2=float(
                np.linalg.norm(arrays['boundary_jump'],axis=1).max()),
            endpoint_jump_unavailable=True)
        report['field_change'] = grouped_metrics(arrays['part_moon']-arrays['part_solid'],
            (arrays['part_moon'][:,4]-arrays['part_moon'][:,3])-(arrays['part_solid'][:,4]-arrays['part_solid'][:,3]),
            times, boundary)
        report['maximum_torque_change_N_m'] = float(np.linalg.norm(arrays['torques'][:,1]-arrays['torques'][:,0],axis=1).max())
        if hashes(sources) != sources or hashes(inputs) != inputs or model_snapshot(seed) != before:
            raise ValueError('Frozen sources, input or seed changed')
        report.update(complete=True, checks_passed=qualification(arrays, numbers, times))
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report['npz_sha256'] = hashes([output.with_suffix('.npz')]).popitem()[1]
        report['wall_seconds'] = perf_counter()-start
        save()
    print('Inertia/field snapshots',len(times),'passed',report['checks_passed'],'seconds',report['wall_seconds'],flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reader-receipt', type=Path, required=True)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    if not run(args.output, args.reader_receipt, args.preflight)['checks_passed']:
        raise RuntimeError('Predeclared field protocol failed; evidence retained')


if __name__ == '__main__':
    main()
