"""Offline observation fit, frozen holdout, independent numerical/physics controls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from scipy.integrate import solve_ivp

from solar_simulator.orbit_determination import (decode_dataset, fit_dataset, fit_orbit,
    evaluate_predictions, predict_directions, angular_residuals, prediction_uncertainty,
    EphemerisBackground, LIGHT_AU_DAY)


def independent_directions(state, observations, document):
    """RK45, separate explicit Hermite formula and force sum, <=0.25-day step.

    This independently checks arithmetic/interpolation/integration/light time;
    shared physical constants/source data are deliberately not independent.
    """
    grid = np.array(document['background']['times_days'])
    bodies = document['background']['bodies']
    positions = np.array([b['positions_au'] for b in bodies]).transpose(1,0,2)
    velocities = np.array([b['velocities_au_day'] for b in bodies]).transpose(1,0,2)
    gm = np.array([b['gm_au3_day2'] for b in bodies])
    def hermite(t):
        i = min(len(grid)-2, int(np.searchsorted(grid,t,side='right'))-1)
        if t < grid[0] or t > grid[-1] or i < 0:
            raise ValueError('Reference background coverage')
        h = grid[i+1]-grid[i]
        u = (t-grid[i])/h
        return ((2*u**3-3*u**2+1)*positions[i]+(u**3-2*u**2+u)*h*velocities[i]
            +(-2*u**3+3*u**2)*positions[i+1]+(u**3-u**2)*h*velocities[i+1])
    def rhs(t,y):
        acceleration = np.zeros(3)
        for mass, source in zip(gm, hermite(t)):
            d = source-y[:3]
            distance = np.sqrt(d[0]**2+d[1]**2+d[2]**2)
            acceleration += mass*d/(distance**3)
        return np.concatenate((y[3:],acceleration))
    times = np.array([o.time_days for o in observations])
    low, high = min(0,min(times)-1), max(0,max(times))
    before = solve_ivp(rhs,(0,low),state,method='RK45',rtol=3e-13,atol=3e-14,max_step=.25,dense_output=True)
    after = solve_ivp(rhs,(0,high),state,method='RK45',rtol=3e-13,atol=3e-14,max_step=.25,dense_output=True)
    if not before.success or not after.success:
        raise RuntimeError('Independent reference failed')
    directions = []
    for o in observations:
        emission = o.time_days
        for _ in range(16):
            value = (before.sol(emission) if emission < 0 else after.sol(emission))[:3]
            direction = value-np.array(o.observer_position_au)
            new = o.time_days-np.sqrt(sum(x*x for x in direction))/LIGHT_AU_DAY
            if abs(new-emission) < 1e-13:
                emission = new
                break
            emission = new
        else:
            raise RuntimeError('Independent light-time failure')
        value = (before.sol(emission) if emission < 0 else after.sol(emission))[:3]-o.observer_position_au
        directions.append(value/np.sqrt(sum(x*x for x in value)))
    return np.array(directions)


def coarsened_background(document):
    bg = document['background']
    indices = list(range(0,len(bg['times_days']),2))
    if indices[-1] != len(bg['times_days'])-1:
        indices.append(len(bg['times_days'])-1)
    return EphemerisBackground(np.array(bg['times_days'])[indices], [b['name'] for b in bg['bodies']],
        [b['gm_au3_day2'] for b in bg['bodies']],
        np.array([b['positions_au'] for b in bg['bodies']]).transpose(1,0,2)[indices],
        np.array([b['velocities_au_day'] for b in bg['bodies']]).transpose(1,0,2)[indices])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=Path('src/solar_simulator/data/orbit-observations-13270.json'))
    parser.add_argument('--output',type=Path,default=Path('docs/orbit-observations-validation.json'))
    args = parser.parse_args(argv)
    started = perf_counter()
    raw = args.dataset.read_bytes()
    document = json.loads(raw)
    training,holdout,background = decode_dataset(document)
    result = fit_dataset(args.dataset)
    state = result['fit']['state_au_day']
    all_obs = training+holdout
    main_residual = angular_residuals(predict_directions(state,all_obs,background),all_obs)
    reference = angular_residuals(independent_directions(state,all_obs,document),all_obs)
    strict = angular_residuals(predict_directions(state,all_obs,background,rtol=3e-13,atol=3e-14),all_obs)
    coarse = angular_residuals(predict_directions(state,all_obs,coarsened_background(document)),all_obs)
    # Baseline also fitted on training only. Both models are reported, never
    # selected or adjusted using holdout residuals. Preferred model declared in advance.
    baseline = fit_orbit(training,background,sun_only=True)
    baseline_metrics = evaluate_predictions(baseline,holdout,background,sun_only=True)
    differences = dict(independent_rk45_max_arcsec=float(np.linalg.norm(main_residual-reference,axis=1).max()),
        stricter_tolerances_max_arcsec=float(np.linalg.norm(main_residual-strict,axis=1).max()),
        background_12h_vs_24h_max_arcsec=float(np.linalg.norm(main_residual-coarse,axis=1).max()))
    result['controls'] = differences | dict(sun_only_training_fit=baseline, sun_only_holdout=baseline_metrics,
        comparison_policy='Both predeclared models use training only; prescribed Sun+planets model is the primary. No model/tolerance/selection tuning to holdout.',
        independent_scope='RK45 with separately coded Hermite interpolation, force sum and light-time iteration; same frozen physical inputs.')
    result['checks_passed'] = bool(result['fit']['rank']==6 and all(v < .001 for v in differences.values()))
    result['dataset_sha256'] = hashlib.sha256(raw).hexdigest()
    result['code_sha256'] = {str(p).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path('src/solar_simulator/orbit_determination.py'),Path(__file__).relative_to(Path.cwd()))}
    result['versions'] = dict(python=sys.version,numpy=np.__version__,scipy=__import__('scipy').__version__)
    result['elapsed_seconds'] = perf_counter()-started
    args.output.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(checks_passed=result['checks_passed'],training_rms_arcsec=result['training']['rms_arcsec'],
        holdout_rms_arcsec=result['holdout']['rms_arcsec'],controls=differences,
        sun_only_holdout_rms_arcsec=baseline_metrics['rms_arcsec'],
        conditional_epoch_sigma_metres=result['holdout_uncertainty']['epoch_position_sigma_trace_metres'],
        elapsed_seconds=result['elapsed_seconds']),indent=2))
    if not result['checks_passed']:
        raise SystemExit('Numerical controls failed; read the report')


if __name__=='__main__':
    main()
