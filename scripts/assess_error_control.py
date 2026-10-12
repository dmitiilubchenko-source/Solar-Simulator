"""Annual control-norm comparison with unchanged forces and initial states.

Default: compute a fresh two-level independent RK45 reference. An explicit
--reuse-reference uses the pinned, previously validated iteration-41 arrays;
it verifies their bytes, source hashes, grid and earlier agreement metrics.
Future JPL vectors enter only after free production integration.
"""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import platform
import time

import numpy as np
import scipy
from scipy.integrate import DOP853

from solar_simulator.perturbers import solar_system_asteroids_catalog
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from scripts.assess_asteroids_catalog import OPTIONS, comparison
from scripts.assess_oblateness import pair_errors
from scripts.assess_orientation import sample
from scripts.assess_pluto import reference
from scripts.assess_relative_coordinates import independent_reference, REFERENCE_SHA256
from scripts.assess_solar_j2 import PLANET_REFERENCE_SHA256, planetary_errors
from scripts.independent_eih_rust import load_oracle
from scripts.independent_figure_vector import acceleration as reference_figures

REFERENCE_ARCHIVE_SHA = '5b688f4f727956a2716c53f49a3e8eb42f017655c7722a0f24baea5d69917188'
STATES_ARCHIVE_SHA = '429a988c4f05fdf6e90343455a6dfade485fab43557dbd6c25e16c1b52cdce85'
PREVIOUS_REPORT_SHA = '98222995ebae229ccb6d66f5a9577c8ac019f94b480e9361b2c15bcbc44dea26'


def checked_bytes(path, expected):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
        raise ValueError('Reference bytes changed: '+str(path))


def cached_reference(initial, origin, times):
    checked_bytes('docs/asteroids-catalog-validation.json', PREVIOUS_REPORT_SHA)
    checked_bytes('.tools/asteroids-catalog-reference.npz', REFERENCE_ARCHIVE_SHA)
    checked_bytes('.tools/asteroids-catalog-states.npz', STATES_ARCHIVE_SHA)
    previous = json.loads(Path('docs/asteroids-catalog-validation.json').read_text(encoding='utf-8'))
    if previous['dataset_sha256'] != origin.dataset_sha256 or not previous['checks_passed']:
        raise ValueError('Reference origin/validation mismatch')
    for path, expected in previous['independent_source_sha256'].items():
        checked_bytes(path, expected)
    with np.load('.tools/asteroids-catalog-reference.npz', allow_pickle=False) as archive:
        if not np.array_equal(times, archive['times']):
            raise ValueError('Reference grid mismatch')
        coarse, fine = archive['level_0'], archive['level_1']
    if fine.shape != (45, 354, 6) or not np.all(np.isfinite(fine)):
        raise ValueError('Invalid independent states')
    convergence = comparison(coarse, fine, initial)
    if convergence != previous['independent_reference_convergence']:
        raise ValueError('Reference convergence does not reproduce previous report')
    with np.load('.tools/asteroids-catalog-states.npz', allow_pickle=False) as archive:
        if not np.array_equal(archive['reference'], fine) or not np.array_equal(times, archive['times']):
            raise ValueError('Prior final report reference mismatch')
        if comparison(archive['all_343_tighter'], fine, initial) != previous['tighter_numerical_agreement']:
            raise ValueError('Prior independent agreement cannot be reproduced')
    return fine, convergence, dict(mode='explicit reuse of validated iteration-41 RK45 reference',
        reference_archive_sha256=REFERENCE_ARCHIVE_SHA, states_archive_sha256=STATES_ARCHIVE_SHA,
        previous_report_sha256=PREVIOUS_REPORT_SHA)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-reference', action='store_true')
    args = parser.parse_args(argv)
    initial, origin = solar_system_asteroids_catalog()
    figures = sun_earth_moon_quadrupoles(initial, origin)
    pair = reference('docs/solar-system-moon-reference.json', REFERENCE_SHA256)
    planets = reference('docs/solar-system-reference.json', PLANET_REFERENCE_SHA256)
    times = (np.array(pair['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    expected = np.stack([np.array([s['position']+s['velocity'] for s in b['states']])
                         for b in pair['bodies']], axis=1)
    if args.reuse_reference:
        independent, convergence, reference_provenance = cached_reference(initial, origin, times)
    else:
        independent, convergence = independent_reference(initial, figures, times,
            levels=((1e-13, 1800.), (3e-14, 900.)), cache_name='error-control-reference',
            acceleration_function=load_oracle(), figure_acceleration_function=reference_figures)
        reference_provenance = dict(mode='fresh independent two-level RK45')
    variants, arrays = {}, {}
    choices = [
        ('global_rms', dict(error_control='global-rms')),
        ('global_rms_strict', dict(error_control='global-rms', position_atol=1e-6, velocity_atol=1e-12)),
        ('per_body', dict(error_control='per-body')),
        ('per_body_strict', dict(error_control='per-body', position_atol=1e-6, velocity_atol=1e-12)),
        ('per_body_stricter', dict(error_control='per-body', position_atol=1e-7, velocity_atol=1e-13)),
    ]
    for name, adjustment in choices:
        start = time.perf_counter()
        options = dict(OPTIONS, **adjustment)
        actual, diagnostics = sample(initial, origin, times, figures, **options)
        arrays[name] = actual
        variants[name] = dict(options=options, elapsed_seconds=time.perf_counter()-start,
            numerical_agreement=comparison(actual, independent, initial),
            jpl_pair=pair_errors(actual, expected, initial, times),
            jpl_planets=planetary_errors(actual, initial, times, planets), **diagnostics)
        print(name, 'seconds', variants[name]['elapsed_seconds'],
              'agreement', variants[name]['numerical_agreement'], flush=True)
    sensitivity = comparison(arrays['per_body_strict'], arrays['per_body_stricter'], initial)
    strict = variants['per_body_stricter']
    agreement = strict['numerical_agreement']
    passed = (agreement['all_bodies']['maximum_position_metres'] < .1
        and agreement['moon_relative_to_earth']['maximum_position_metres'] < .02
        and sensitivity['all_bodies']['maximum_position_metres'] < .1
        and sensitivity['moon_relative_to_earth']['maximum_position_metres'] < .02
        and strict['maximum_relative_energy_budget_residual'] < 1e-10)
    source_files = ['src/solar_simulator/error_control.py', 'src/solar_simulator/accuracy.py',
                    'src/solar_simulator/native_forces.py', 'rust/solar_core/src/relativity.rs',
                    'scripts/independent_figure_vector.py', 'scripts/validation/eih_scalar.rs',
                    'scripts/assess_relative_coordinates.py', 'scripts/assess_error_control.py']
    report = dict(dataset_sha256=origin.dataset_sha256, gm_sha256=origin.gm_sha256,
        epoch_jd_tdb=origin.epoch_jd_tdb, duration_seconds=float(times[-1]), samples=len(times),
        body_count=len(initial), physics='same 354 bodies / EIH 1PN / prescribed Sun-Earth-Moon quadrupoles',
        runtime=dict(python=platform.python_version(), scipy=scipy.__version__, numpy=np.__version__),
        reference_provenance=reference_provenance, independent_reference_convergence=convergence,
        scipy_global_norm_source_sha256=hashlib.sha256(inspect.getsource(DOP853._estimate_error_norm).encode()).hexdigest(),
        recommended_variant='per_body_stricter', variants=variants, tolerance_sensitivity=sensitivity,
        checks_passed=passed, source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in source_files},
        limitations=['Local error estimate is not a global guarantee.',
            '45 sampled states, not a continuous supremum.',
            'The independent reference has its own convergence uncertainty.',
            'No new forces or fitted physical parameters in this iteration.'])
    Path('docs/error-control-validation.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    np.savez_compressed('.tools/error-control-states.npz', times=times, reference=independent, **arrays)
    print('checks_passed', passed, 'sensitivity', sensitivity, flush=True)
    if not passed:
        raise RuntimeError('Per-body annual numerical validation failed')


if __name__ == '__main__':
    main()
