"""Short, source-resolved Noether pilot for the unchanged nominal ten-body model."""
import argparse
from dataclasses import asdict
from importlib import import_module
import json
from pathlib import Path
from statistics import median
from time import perf_counter
import warnings

import numpy as np

from scripts.assess_edited_solar import oracle_check
from scripts.assess_edited_solar_month import candidate_metrics, reference_gate, finite_states
from scripts.assess_nominal_solar_packets import versions
from scripts.assess_sandbox_models import load_oracle, figure_reference
from scripts.assess_sandbox_planets import states
from scripts.edited_j2 import legacy_trajectory, checkpoint_check
from scripts.eih_year import force_terms
from scripts.fixed_j2_ias import (entries, figure_force, potential, reference,
    quantities, scales, balances, dop_trajectory)
from scripts.fixed_j2_year import inputs, within
from scripts.newton_year import ROOT, NAMES, hashes, agreement, YEAR
from solar_simulator.native_forces import prepare as native_prepare
from solar_simulator.oblateness import acceleration, prepare, orbital_torque
from solar_simulator.relativity import C
from solar_simulator.simulation import AU, G
from solar_simulator.storage import to_document

PROTOCOL = 'docs/solar-noether-pilot-protocol.md'
DURATION = 259200.
LEVELS = (1800., 900., 450.)
GROUPS = ('figure_torque', 'pn2', 'pn_q2')
BLOCKS = (('energy', slice(0, 1)), ('momentum', slice(1, 4)), ('angular', slice(4, 7)))


def epoch_grid():
    return np.r_[np.arange(0., DURATION, 72000.), DURATION]


def packet_check(stats):
    np.testing.assert_array_equal(stats['packet_endpoints'], epoch_grid()[1:])
    if stats['packets'] != 4 or not stats['finished'] or stats['failed']:
        raise ValueError('Incomplete three-day packet grid')


def snapshot_controls(seed):
    q = states(seed.bodies)
    p, v = q[:, :3], q[:, 3:]
    m = np.array([b.mass for b in seed.bodies])
    fig = entries(seed)
    tensor = figure_force(p, m, fig)
    vector = figure_reference(p / AU, G*m*YEAR**2/AU**3, seed.settings.figures,
        list(NAMES), 0.) * AU / YEAR**2
    actual = acceleration(p, m, prepare(seed.bodies, seed.settings.figures))
    field_scale = np.linalg.norm(tensor, axis=1).max()
    gradient = np.zeros_like(p)
    for i in range(len(m)):
        for k in range(3):
            changed = p.astype(complex)
            changed[i, k] += 1e-6j
            gradient[i, k] = potential(changed, m, fig).imag / 1e-6
    force = m[:, None] * tensor
    force_scale = np.linalg.norm(force, axis=1).sum()
    missing = force.copy()
    missing[[i for i, _, _ in fig]] = 0.
    torque = np.cross(p, force).sum(axis=0)
    working_torque = orbital_torque(seed.bodies, seed.settings.figures)
    torque_scale = np.sum(np.linalg.norm(p, axis=1) * np.linalg.norm(force, axis=1))
    point = native_prepare(m)
    n, pn = force_terms(p, v, G*m, C)
    _, strong = force_terms(p, v, G*m, C/10)
    amplified = point(p, v, C/10) - point(p, v)
    row = dict(tensor_vector_relative_error=float(np.linalg.norm(tensor-vector, axis=1).max()/field_scale),
        tensor_runtime_relative_error=float(np.linalg.norm(tensor-actual, axis=1).max()/field_scale),
        potential_gradient_relative_error=float(np.linalg.norm(tensor+gradient/m[:, None], axis=1).max()/field_scale),
        correct_scaled_net_force=float(np.linalg.norm(force.sum(axis=0))/force_scale),
        missing_source_scaled_net_force=float(np.linalg.norm(missing.sum(axis=0))/force_scale),
        torque_relative_error=float(np.linalg.norm(torque-[working_torque.x,working_torque.y,working_torque.z])/torque_scale),
        full_eih_relative_error=float(np.linalg.norm(point(p,v,C)-n-pn, axis=1).max()/np.linalg.norm(n+pn,axis=1).max()),
        amplified_pn_relative_error=float(np.linalg.norm(amplified-strong,axis=1).max()/np.linalg.norm(strong,axis=1).max()))
    row['checks_passed'] = bool(all(row[k] < 5e-13 for k in ('tensor_vector_relative_error',
        'tensor_runtime_relative_error','potential_gradient_relative_error','correct_scaled_net_force','torque_relative_error'))
        and row['missing_source_scaled_net_force'] > 1e-3 and row['full_eih_relative_error'] < 3e-14
        and row['amplified_pn_relative_error'] < 3e-9)
    return row


def budget_refinement(previous, current, scale):
    if (previous.shape != current.shape or current.ndim != 3 or current.shape[1:] != (3, 7)
            or not np.isfinite(previous).all() or not np.isfinite(current).all()
            or np.shape(scale) != (7,) or not np.isfinite(scale).all() or not (scale > 0).all()):
        raise ValueError('Invalid budget dimensions, values or scales')
    result = {}
    for i, group in enumerate(GROUPS):
        result[group] = {}
        for name, block in BLOCKS:
            signal = float(np.linalg.norm(current[:, i, block] / scale[block], axis=1).max())
            difference = float(np.linalg.norm((current[:, i, block]-previous[:, i, block])/scale[block], axis=1).max())
            relative = difference/signal if signal else (0. if difference == 0. else None)
            result[group][name] = dict(signal=signal, scaled_difference=difference, relative_difference=relative,
                active=bool(signal), checks_passed=bool(relative is not None and relative < 1e-3))
    maximum = float(np.max(np.abs((current-previous)/scale)))
    return dict(groups=result, maximum_scaled_component=maximum,
        checks_passed=bool(maximum < 1e-12 and all(r['checks_passed'] for g in result.values() for r in g.values())))


def normalized_balance(values, budget, seed):
    if budget.shape != (len(values), 3, 7) or not np.isfinite(budget).all():
        raise ValueError('Invalid source budgets')
    m = np.array([b.mass for b in seed.bodies])
    scale = scales(values[0], m, entries(seed), seed.settings.physics)
    if not np.isfinite(scale).all() or not (scale > 0).all():
        raise ValueError('Nonpositive/nonfinite Noether scales')
    rows = np.array([quantities(q, m, entries(seed), seed.settings.physics) for q in values])
    delta = (rows-rows[0]) / scale
    residual = delta - budget.sum(axis=1) / scale
    return scale, delta, residual


def observability(last_values, last_budget, previous_values, previous_budget, seed):
    scale, delta, corrected = normalized_balance(last_values, last_budget, seed)
    _, _, old_corrected = normalized_balance(previous_values, previous_budget, seed)
    groups = {}
    for i, group in enumerate(GROUPS):
        groups[group] = {}
        omitted = delta - (last_budget.sum(axis=1)-last_budget[:, i])/scale
        for name, block in BLOCKS:
            signal = float(np.linalg.norm(last_budget[:, i, block]/scale[block], axis=1).max())
            residual = float(np.linalg.norm(corrected[:, block], axis=1).max())
            sensitivity = float(np.linalg.norm((corrected-old_corrected)[:, block], axis=1).max())
            floor = max(32*np.finfo(float).eps, residual, sensitivity)
            groups[group][name] = dict(active=bool(signal), scaled_signal=signal,
                scaled_resolution=floor, signal_to_resolution=signal/floor,
                omitted_scaled_residual=float(np.linalg.norm(omitted[:, block], axis=1).max()),
                checks_passed=bool(not signal or signal/floor > 10.))
    return dict(groups=groups, resolution_is_rigorous_bound=False,
        checks_passed=all(row['checks_passed'] for g in groups.values() for row in g.values()))


def run(output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or any(output.with_suffix(s).exists() for s in ('.json','.npz')):
        raise ValueError('Use fresh project .tools output; preserve prior evidence')
    output.parent.mkdir(parents=True, exist_ok=True)
    seed, _, _, _, preflight = inputs()
    initial, times, before = states(seed.bodies), epoch_grid(), to_document(seed)
    prior = json.loads((ROOT/'docs/fixed-j2-ias-validation.json').read_bytes())['measurements']
    if hashes(prior['source_sha256']) != prior['source_sha256']:
        raise ValueError('Frozen budget implementation changed')
    paths = [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    paths += [*prior['source_sha256'], PROTOCOL,'scripts/assess_solar_noether.py','tests/test_solar_noether.py',
        'scripts/assess_nominal_solar_packets.py','scripts/fixed_j2_year.py','scripts/independent_figure_vector.py']
    sources = hashes(paths)
    bindings = hashes([*preflight['inputs_sha256'],'docs/fixed-j2-ias-validation.json'])
    oracle = load_oracle()
    import scipy.integrate._ivp.rk as rk
    import scipy.integrate._ivp.base as base
    dependencies = hashes([*(Path(import_module(n).__file__) for n in ('solar_native','solar_native.solar_native')),
        Path(rk.__file__),Path(base.__file__),ROOT/'.tools'/('independent-eih-'+oracle.source_sha256[:16]+'.dll')])
    report = dict(protocol=PROTOCOL, complete=False, checks_passed=False, phase='preflight',
        source_sha256=sources,input_sha256=bindings,dependency_sha256=dependencies,
        origin=asdict(seed.origin),settings=asdict(seed.settings),names=list(NAMES),masses_kg=[b.mass for b in seed.bodies],
        snapshot_controls=snapshot_controls(seed),oracle_snapshot=oracle_check(seed,oracle),
        epochs_seconds=times.tolist(),reference_levels=[],reference_comparisons={},candidates={},
        runtime_modified=False,general_release=False,annual_balances_verified=False,jpl_comparison=False)
    arrays = dict(times=times,initial=initial)

    def save():
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        report['npz_sha256'] = hashes([output.with_suffix('.npz')]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')

    save()
    try:
        if not report['snapshot_controls']['checks_passed'] or not report['oracle_snapshot']['checks_passed']:
            raise RuntimeError('Model/force preflight failed')
        scale = scales(initial,np.array([b.mass for b in seed.bodies]),entries(seed),seed.settings.physics)
        report['scales_SI'] = scale.tolist()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            report['phase'] = 'references'
            for i, cap in enumerate(LEVELS):
                start = perf_counter()
                values, budget, meta = reference(seed,times,3e-14,cap)
                finite_states(values,times)
                if not np.isfinite(budget).all() or np.any(budget[0]):
                    raise ValueError('Invalid reference source integral')
                arrays['reference_'+str(i)], arrays['budget_'+str(i)] = values,budget
                meta['wall_seconds'] = perf_counter()-start
                report['reference_levels'].append(meta)
                save()
                print('reference',i,meta,flush=True)
            for i in (1,2):
                report['reference_comparisons'][f'{i-1}_to_{i}'] = dict(
                    state=agreement(arrays['reference_'+str(i-1)],arrays['reference_'+str(i)],list(NAMES)),
                    budgets=budget_refinement(arrays['budget_'+str(i-1)],arrays['budget_'+str(i)],scale))
            last = report['reference_comparisons']['1_to_2']
            expected,budget = arrays['reference_2'],arrays['budget_2']
            initial_error = agreement(expected[:1],initial[None],list(NAMES))
            calls = [r['rhs_calls'] for r in report['reference_levels']]
            ref_ok = reference_gate(last['state'],initial_error,calls,report['oracle_snapshot']) and last['budgets']['checks_passed']
            ref_balance = balances(expected,budget,seed)
            ref_ok = bool(ref_ok and max(ref_balance['corrected'].values()) < 1e-10)
            report.update(reference_passed=ref_ok,reference_initial_roundtrip=initial_error,reference_balance=ref_balance,
                source_observability=observability(expected,budget,arrays['reference_1'],arrays['budget_1'],seed))
            save()
            if not ref_ok:
                raise RuntimeError('Reference state/budget qualification failed')
            report['phase'] = 'candidates'
            modes = versions(seed)
            functions = {'legacy_python':lambda:legacy_trajectory(modes['python'],times),
                'legacy_rust':lambda:legacy_trajectory(modes['rust'],times),
                'continuous_rust':lambda:dop_trajectory(modes['rust'],times)}
            for name,function in functions.items():
                values,stats = function()
                finite_states(values,times)
                packet_check(stats)
                np.testing.assert_array_equal(values[0].view(np.uint64),initial.view(np.uint64))
                repeated,other = function()
                np.testing.assert_array_equal(values.view(np.uint64),repeated.view(np.uint64))
                packet_check(other)
                arrays[name] = values
                row = candidate_metrics(values,expected)
                balance = balances(values,budget,seed)
                row.update(balance=balance,statistics=stats,repeat_bitexact=True,
                    checks_passed=bool(row['checks_passed'] and max(balance['corrected'].values()) < 1e-10),
                    legacy_checkpoint_continue_exact=(checkpoint_check(modes[name.removeprefix('legacy_')],144000.)
                        if name.startswith('legacy_') else None))
                report['candidates'][name] = row
                print(name,row['moon_relative_to_earth'],balance['corrected'],'passed',row['checks_passed'],flush=True)
                save()
            durations = {name:[] for name in functions}
            for iteration in range(3):
                for name in (list(functions) if iteration%2==0 else list(reversed(functions))):
                    start = perf_counter()
                    values,stats = functions[name]()
                    durations[name].append(perf_counter()-start)
                    packet_check(stats)
                    np.testing.assert_array_equal(values.view(np.uint64),arrays[name].view(np.uint64))
            report['cost'] = {name:dict(seconds=v,median_seconds=median(v)) for name,v in durations.items()}
            report['warnings'] = [str(w.message) for w in caught]
        if any(hashes(group)!=group for group in (sources,bindings,dependencies)) or to_document(seed)!=before:
            raise ValueError('Scientific source/input/actual dependency or seed changed')
        numerical = bool(ref_ok and all(r['checks_passed'] for r in report['candidates'].values()))
        report.update(phase='complete',complete=True,source_input_dependencies_unchanged=True,
            numerical_checks_passed=numerical,full_source_observability_passed=report['source_observability']['checks_passed'],
            checks_passed=bool(numerical and report['source_observability']['checks_passed']))
        save()
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__,message=str(error))
        save()
        raise
    print('complete',output,'numerical',report['numerical_checks_passed'],
        'source visibility',report['full_source_observability_passed'],flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if not run(args.output)['checks_passed']:
        raise RuntimeError('Declared pilot criteria not all passed; evidence retained')


if __name__ == '__main__':
    main()
