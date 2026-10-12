"""Validate working Rust forces and DOP853 orbits against separate RK45/EIH."""
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time

import numpy as np
from solar_simulator.native_forces import prepare
from solar_simulator.accuracy import evolve_accurate
from solar_simulator.diagnostics import model_invariants
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from solar_simulator.perturbers import solar_system_asteroids_full
from solar_simulator.relativity import C, _eih_acceleration
from solar_simulator.simulation import G

if __package__:
    from .assess_orientation import sample
    from .assess_relative_coordinates import independent_reference, relative_states, REFERENCE_SHA256
    from .assess_resolved_moon import errors, states
    from .fetch_asteroid_catalog import trial_system, INITIAL_SHA
    from .independent_eih_rust import load_oracle
else:
    from assess_orientation import sample
    from assess_relative_coordinates import independent_reference, relative_states, REFERENCE_SHA256
    from assess_resolved_moon import errors, states
    from fetch_asteroid_catalog import trial_system, INITIAL_SHA
    from independent_eih_rust import load_oracle


OPTIONS = dict(relative_pair=('Earth', 'Moon'), rtol=3e-14,
               position_atol=1e-5, velocity_atol=1e-11)


def comparison(first, second, initial):
    return dict(all_bodies=errors(first, second),
        moon_relative_to_earth=errors(relative_states(first, initial), relative_states(second, initial)))


def profile(initial):
    q = states(initial)
    masses = np.array([b.mass for b in initial])
    names = [b.name for b in initial]
    e, m = names.index('Earth'), names.index('Moon')
    pair = (e, m, q[m, :3]-q[e, :3])
    rust = prepare(masses)
    def python(): return _eih_acceleration(q[:, :3], q[:, 3:], masses, C, pair)
    def native(): return rust(q[:, :3], q[:, 3:], C, pair)
    difference = float(np.max(np.abs(python()-native())))
    if difference > 3e-16:
        raise RuntimeError('Working force mismatch')
    timings = {}
    for name, function in (('python', python), ('rust', native)):
        function()
        batches = []
        for _ in range(5):
            start = time.perf_counter()
            for _ in range(20): function()
            batches.append((time.perf_counter()-start)/20)
        timings[name] = statistics.median(batches)
    return dict(callback_median_seconds=timings,
        callback_speedup=timings['python']/timings['rust'],
        maximum_acceleration_difference_m_per_s2=difference,
        includes_python_adapter_and_owned_copy=True)


def sample_trial(initial, times, figures, *, backend, **options):
    """Unregistered source trials carry no false runtime dataset origin."""
    bodies, current, work = initial, 0., 0.
    e0 = model_invariants(initial, 'eih-1pn', figures)[0]
    values, budget, raw = [], 0., 0.
    for target in times:
        if target > current:
            bodies, delta = evolve_accurate(bodies, float(target-current), physics='eih-1pn',
                figures=figures, start_time=current, return_work=True, backend=backend, **options)
            work += delta
            current = float(target)
        values.append(states(bodies))
        energy = model_invariants(bodies, 'eih-1pn', figures, current)[0]
        budget = max(budget, abs((energy-work-e0)/e0))
        raw = max(raw, abs((energy-e0)/e0))
    return np.array(values), dict(maximum_relative_energy_budget_residual=budget,
        maximum_relative_raw_energy_change=raw, final_orientation_work_joules=work)


def validate(initial, origin, times, name, *, figures=None, reference_result=None):
    figures = sun_earth_moon_quadrupoles(initial, origin) if figures is None else figures
    measured, values = {}, {}
    for backend, options in (('python', OPTIONS), ('rust', OPTIONS),
            ('rust_tighter', dict(OPTIONS, position_atol=1e-6, velocity_atol=1e-12))):
        start = time.perf_counter()
        settings = dict(backend='rust' if backend.startswith('rust') else 'python', **options)
        actual, diagnostics = (sample(initial, origin, times, figures, **settings) if origin is not None
            else sample_trial(initial, times, figures, **settings))
        measured[backend] = dict(elapsed_seconds=time.perf_counter()-start, **diagnostics)
        values[backend] = actual
        print(name, backend, measured[backend]['elapsed_seconds'], flush=True)
    reference, convergence = reference_result or independent_reference(initial, figures, times,
        levels=((1e-13, 1800.), (3e-14, 900.)), cache_name='native-eih-'+name,
        acceleration_function=load_oracle())
    report = dict(body_count=len(initial), duration_seconds=float(times[-1]), samples=len(times),
        production=measured, options=OPTIONS, reference_convergence=convergence,
        rust_vs_python=comparison(values['rust'], values['python'], initial),
        rust_tolerance_sensitivity=comparison(values['rust'], values['rust_tighter'], initial),
        rust_vs_independent=comparison(values['rust'], reference, initial),
        force_profile=profile(initial))
    report['integration_speedup'] = measured['python']['elapsed_seconds']/measured['rust']['elapsed_seconds']
    report['orientation_work_relative_difference'] = abs(
        measured['rust']['final_orientation_work_joules']-measured['python']['final_orientation_work_joules'])/max(
        abs(measured['python']['final_orientation_work_joules']),1.)
    report['checks_passed'] = all(
        report[key]['all_bodies']['maximum_position_metres'] < .1
        and report[key]['moon_relative_to_earth']['maximum_position_metres'] < .05
        and report[key]['all_bodies']['maximum_velocity_m_per_s'] < 1e-6
        for key in ('rust_vs_python', 'rust_tolerance_sensitivity', 'rust_vs_independent')) and (
        measured['rust']['maximum_relative_energy_budget_residual']<1e-10
        and report['orientation_work_relative_difference']<1e-8)
    np.savez_compressed(Path('.tools')/('native-eih-'+name+'-states.npz'), times=times,
        reference=reference, **values)
    print(name, 'agreement', report['rust_vs_independent'], 'passed', report['checks_passed'], flush=True)
    return report


def main(*, year_reference=None):
    source = Path('docs/solar-system-moon-reference.json')
    if hashlib.sha256(source.read_bytes()).hexdigest() != REFERENCE_SHA256:
        raise ValueError('Pinned 45-epoch reference changed')
    doc = json.loads(source.read_text(encoding='utf-8'))
    initial, origin = solar_system_asteroids_full()
    times = (np.array(doc['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    if len(times) != 45 or times[0] != 0 or times[-1] != 31557600 or np.any(np.diff(times) <= 0):
        raise ValueError('Wrong yearly validation grid')
    Path('.tools').mkdir(exist_ok=True)
    year = validate(initial, origin, times, '27-year', reference_result=year_reference)
    large = trial_system(json.loads(Path('docs/asteroids-343-initial.json').read_text(encoding='utf-8')))
    day = validate(large, None, np.array([0., 21600., 43200., 86400.]), '354-day',
        figures=sun_earth_moon_quadrupoles(initial, origin))
    files = ('rust/solar_core/src/relativity.rs', 'rust/solar_native/src/lib.rs',
        'src/solar_simulator/native_forces.py', 'src/solar_simulator/accuracy.py',
        'scripts/validation/eih_scalar.rs', 'scripts/assess_native_eih.py',
        'scripts/assess_relative_coordinates.py', 'scripts/assess_orientation.py')
    result = dict(scope='Working Newton/EIH Rust force; SciPy DOP853 and figures in Python',
        python=platform.python_version(), machine=platform.machine(),
        initial_27_sha256=origin.dataset_sha256, initial_343_sha256=INITIAL_SHA,
        validation_grid_sha256=REFERENCE_SHA256,
        source_sha256={path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in files},
        year_27=year, day_354=day, checks_passed=year['checks_passed'] and day['checks_passed'],
        limitations=['Same physical model; port does not remove omitted physical effects.',
            '354-body trial is checked over one day, not a year.',
            'Timings describe this computer and are not universal speed guarantees.',
            'No future JPL vectors enter the working or independent orbit integration.'])
    Path('docs/native-eih-validation.json').write_text(json.dumps(result, ensure_ascii=False,
        indent=2, allow_nan=False)+'\n', encoding='utf-8')
    if not result['checks_passed']: raise RuntimeError('Native orbit validation failed')


if __name__ == '__main__':
    main()
