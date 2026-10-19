"""Frozen synthetic EIH/rotor trajectories and source-resolved balances."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

from scripts import hybrid_rotation as model_code
from scripts import independent_hybrid_rotation as reference
from scripts import decimal_hybrid_rotation as decimal_check
from scripts.newton_year import ROOT, hashes
from solar_simulator.relativity import eih_acceleration

PROTOCOL = 'docs/hybrid-rotation-protocol.md'
MODES = ('order-reduced', 'finite-action')


def matrices(values, n):
    return Rotation.from_quat(values[:, 6*n:6*n+4][:, [1, 2, 3, 0]]).as_matrix()


def reference_state(values, n):
    r = values[:, 6*n:6*n+9].reshape(-1, 3, 3)
    spin = np.einsum('tij,tj->ti', r, values[:, 6*n+9:6*n+12])
    return np.c_[values[:, :6*n], np.zeros((len(values), 4)), spin, values[:, 6*n+12:]], r


def error(first, second, first_r, second_r, block_scales, n):
    if first.shape != second.shape or first_r.shape != second_r.shape or not all(
            np.isfinite(a).all() for a in (first, second, first_r, second_r)):
        raise ValueError('Matching finite trajectory arrays required')
    orbit = np.linalg.norm((first[:, :6*n]-second[:, :6*n]).reshape(-1, 2*n, 3), axis=-1)/block_scales[:2*n]
    spin = np.linalg.norm(first[:, 6*n+4:6*n+7]-second[:, 6*n+4:6*n+7], axis=1)/block_scales[2*n]
    attitude = np.linalg.norm(first_r-second_r, axis=(1, 2))
    return dict(orbit_per_body=orbit.max(axis=0).tolist(), spin=float(spin.max()),
        attitude=float(attitude.max()), maximum=float(max(orbit.max(), spin.max(), attitude.max())))


def norms(values, scales):
    values = values/scales
    return dict(energy=float(abs(values[:, 0]).max()), momentum=float(np.linalg.norm(values[:, 1:4], axis=1).max()),
        angular=float(np.linalg.norm(values[:, 4:], axis=1).max()))


def balances(values, rotation, model, scales):
    rows = np.array([reference.quantities(y, model.masses, model.c, model.moments,
        model.source, r) for y, r in zip(values, rotation)])
    delta = rows-rows[0]
    budgets = values[:, 6*len(model.masses)+7:].reshape(-1, 2, 7)
    return dict(raw=norms(delta, scales), corrected=norms(delta-budgets.sum(axis=1), scales),
        sources={k:norms(budgets[:, i], scales) for i, k in enumerate(('pn2', 'pn_q2'))})


def visibility(values, previous, reference_values, rotation, model, scales):
    n = len(model.masses)
    arrays = [y[:, 6*n+7:].reshape(-1, 2, 7) for y in (values, previous, reference_values)]
    corrected = balances(values, rotation, model, scales)['corrected']
    totals = np.array([reference.quantities(y, model.masses, model.c, model.moments,
        model.source, r) for y, r in zip(values, rotation)])
    residual = totals-totals[0]-arrays[0].sum(axis=1)
    rows = {}
    for i, name in enumerate(('pn2', 'pn_q2')):
        signal = norms(arrays[0][:, i], scales)
        uncertainty = norms(arrays[0][:, i]-arrays[1][:, i], scales)
        other = norms(arrays[0][:, i]-arrays[2][:, i], scales)
        omitted = norms(residual+arrays[0][:, i], scales)
        rows[name] = {}
        for block in ('energy', 'momentum', 'angular'):
            noise = uncertainty[block]+other[block]+corrected[block]
            rows[name][block] = dict(signal=signal[block], numerical_budget=noise,
                omitted_source_balance=omitted[block], corrected_balance=corrected[block],
                checks_passed=bool(signal[block] > 32*np.finfo(float).eps and signal[block] > 10*noise
                    and omitted[block] > 10*corrected[block]))
    return dict(sources=rows, checks_passed=all(r['checks_passed'] for group in rows.values() for r in group.values()))


def algebra(state, model):
    x, v, q, s = model_code.unpack(state, model); m = np.array(model.masses)
    n, pn = model_code.force_terms(x, v, m, model.c)
    aq, torque, _ = model_code.figure_field(x, m, q, model)
    h = model_code.hessian(x, v, m, model.c)
    independent_h, k = reference.derivatives(x, v, m, model.c)
    r = Rotation.from_quat(q[[1, 2, 3, 0]]).as_matrix()
    f, tau_body, _ = reference.body_field(x, m, r, model.moments, model.source, model.radius)
    unit = model_code.UNITS
    runtime = eih_acceleration(x*unit.length_m, v*unit.velocity_m_s, m*unit.mass_kg,
        c=float(model.c*unit.velocity_m_s))/(unit.length_m/unit.time_s**2)
    gap = lambda a,b: float(np.linalg.norm(a-b)/np.linalg.norm(b)) if np.linalg.norm(b) else (0. if not np.linalg.norm(a) else None)
    strong_h = model_code.hessian(x, v, m, 2*model.c)
    _, small_pn = model_code.force_terms(x, v, m, 2*model.c)
    b2 = h@pn.ravel(); bq = h@aq.ravel()
    rows = dict(runtime_full=gap(runtime, n+pn), isolated_pn=gap(runtime-n, pn),
        q_force=gap(aq*m[:, None], f), q_torque=gap(torque, r@tau_body),
        velocity_hessian=gap(h, independent_h), point_action=gap(k, (m[:, None]*(n+pn)).ravel().reshape(-1, 3)
            +(h@n.ravel()).reshape(-1, 3)),
        pn2_order=gap(16*strong_h@small_pn.ravel(), b2), pn_q2_order=gap(4*strong_h@aq.ravel(), bq))
    rows['checks_passed'] = bool(all(rows[k] is not None and rows[k] < (
        3e-14 if k == 'runtime_full' else 1e-9 if k == 'isolated_pn' else 5e-12) for k in rows))
    return rows


def qualification(report):
    jobs = {mode+'-'+suffix for mode in MODES for suffix in ('nominal', 'tight', 'ref0', 'ref1')}
    if (not report.get('complete') or set(report.get('cases', {})) != set(MODES)
            or set(report.get('jobs', {})) != jobs or len(report.get('times', [])) != 129
            or [r.get('index') for r in report.get('identities', [])] != list(range(0, 129, 16))
            or [r.get('index') for r in report.get('algebra', [])] != list(range(0, 129, 16))):
        return False
    return bool(all(case.get('checks_passed', False) for case in report['cases'].values())
        and all(r['checks_passed'] and r['low']['checks_passed'] and r['high']['checks_passed']
            for r in report['identities']) and all(r['checks_passed'] for r in report['algebra'])
        and report['source_visibility']['checks_passed']
        and max(r['high']['missing_spin_torque_relative'] for r in report['identities']) > 1e-3)


def run(output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or output.with_suffix('.json').exists() or output.exists():
        raise ValueError('Use fresh project .tools output; preserve failures')
    model = model_code.Model(); start = model_code.initial(model); n = len(model.masses)
    r0 = matrices(start[None, :], n)[0]
    base = reference.quantities(start, model.masses, model.c, model.moments, model.source, r0)
    momentum_scale = np.sum(np.array(model.masses)*np.linalg.norm(start[3*n:6*n].reshape(n, 3), axis=1))
    scales = np.r_[abs(base[0]), [momentum_scale]*3, [np.linalg.norm(base[4:])]*3]
    blocks = np.r_[np.linalg.norm(start[:6*n].reshape(2*n, 3), axis=1), np.linalg.norm(start[6*n+4:6*n+7])]
    if not (scales > 0).all() or not (blocks > 0).all():
        raise ValueError('Nonzero declared initial scales required')
    atol_scale = np.r_[np.repeat(blocks[:2*n], 3), np.ones(4), [blocks[-1]]*3, np.tile(scales, 2)]
    ref_start = np.r_[start[:6*n], r0.ravel(), r0.T@start[6*n+4:6*n+7], np.zeros(14)]
    ref_scale = np.r_[np.repeat(blocks[:2*n], 3), np.ones(9), [blocks[-1]]*3, np.tile(scales, 2)]
    times = np.linspace(0., 4*np.pi, 129)
    sources = {str(Path(m.__file__).resolve().relative_to(ROOT)) for m in tuple(sys.modules.values())
        if getattr(m, '__file__', None) and str(m.__file__).endswith('.py')
        and Path(m.__file__).resolve().is_relative_to(ROOT)
        and Path(m.__file__).resolve().parts[len(ROOT.parts)] in ('scripts', 'src')}
    bound = hashes(sorted(sources | {PROTOCOL}))
    report = dict(complete=False, checks_passed=False, protocol=PROTOCOL, source_sha256=bound,
        model=asdict(model), numpy=np.__version__, scipy=scipy.__version__, python=sys.version,
        initial_state=start.tolist(), times=times.tolist(), scales=scales.tolist(), cases={}, jobs={},
        runtime_modified=False, parameters_fitted=False, lunar_physical_mapping_certified=False,
        jpl_comparison=False, network_used=False, exact_finite_action_is_complete_gr=False,
        ten_body_annual_balances_qualified=False)
    output.parent.mkdir(parents=True, exist_ok=True); output.mkdir()
    arrays = dict(times=times); clock = perf_counter()

    def save():
        output.with_suffix('.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf8')

    def job(name, fun, y0, tolerance, maximum_step, scale, method):
        if hashes(bound) != bound:
            raise ValueError('Frozen code changed before job')
        print(name, 'started', flush=True); tick = perf_counter()
        extra = dict(body_count=n) if method is model_code.HybridDOP853 else {}
        sol = solve_ivp(fun, (0., float(times[-1])), y0, t_eval=times, method=method,
            rtol=tolerance, atol=.01*tolerance*scale, max_step=maximum_step, **extra)
        if not sol.success or sol.y.shape != (len(y0), 129) or not np.array_equal(sol.t, times) or not np.isfinite(sol.y).all():
            raise ValueError('Invalid/failed scientific job: '+name)
        path = output/(name+'.npz'); np.savez_compressed(path, times=times, state=sol.y.T)
        report['jobs'][name] = dict(rtol=tolerance, maximum_step=maximum_step, method=sol.message,
            solver='worst-block DOP853' if extra else 'RK45', nfev=sol.nfev,
            wall_seconds=perf_counter()-tick, npz_sha256=hashes([path]).popitem()[1])
        arrays[name] = sol.y.T; save()
        print(name, 'done', round(report['jobs'][name]['wall_seconds'], 3), 's', flush=True)
        return sol.y.T

    save()
    try:
        for mode in MODES:
            prod_fun = lambda t,y: model_code.rhs(t, y, model, mode)
            nominal = job(mode+'-nominal', prod_fun, start, 1e-10, 2*np.pi/64, atol_scale, model_code.HybridDOP853)
            tight = job(mode+'-tight', prod_fun, start, 3e-12, 2*np.pi/128, atol_scale, model_code.HybridDOP853)
            ref_fun = lambda t,y: reference.rhs(t, y, model.masses, model.c, model.moments, model.source, model.radius, mode)
            raw_refs = [job(mode+'-ref'+str(k), ref_fun, ref_start, tol, 2*np.pi/128, ref_scale, 'RK45')
                for k, tol in enumerate((3e-12, 3e-13))]
            refs = [reference_state(y, n) for y in raw_refs]
            rn, rt = matrices(nominal, n), matrices(tight, n)
            comparison = error(nominal, refs[-1][0], rn, refs[-1][1], blocks, n)
            uncertainty = error(*[refs[0][0], refs[1][0], refs[0][1], refs[1][1]], blocks, n)
            sensitivity = error(nominal, tight, rn, rt, blocks, n)
            audit_balances = {k:balances(v, r, model, scales) for k, v, r in (
                ('nominal', nominal, rn), ('tight', tight, rt), ('ref0', *refs[0]), ('ref1', *refs[1]))}
            qnorm = max(float(abs(np.linalg.norm(y[:, 6*n:6*n+4], axis=1)-1).max()) for y in (nominal, tight))
            orth = max(float(np.linalg.norm(r.transpose(0,2,1)@r-np.eye(3), axis=(1,2)).max()) for _,r in refs)
            determinant = max(float(abs(np.linalg.det(r)-1).max()) for _,r in refs)
            row = dict(comparison=comparison, reference_uncertainty=uncertainty, tighter_sensitivity=sensitivity,
                balances=audit_balances, qnorm=qnorm, orthogonality=orth, determinant=determinant)
            row['checks_passed'] = bool(comparison['maximum'] < 3e-7 and uncertainty['maximum'] < 3e-8
                and sensitivity['maximum'] < 3e-8 and max(qnorm, orth, determinant) < 1e-8
                and all(max(b['corrected'].values()) < 1e-9 for b in audit_balances.values()))
            report['cases'][mode] = row
            if mode == 'order-reduced':
                report['source_visibility'] = visibility(tight, nominal, refs[-1][0], rt, model, scales)
                report['identities'], report['algebra'] = [], []
                for index in range(0, 129, 16):
                    y = tight[index]
                    low = decimal_check.snapshot(y, model, 70); high = decimal_check.snapshot(y, model, 90)
                    agreement = decimal_check.precision_agreement(low, high)
                    report['identities'].append(dict(index=index, low=low, high=high,
                        precision_agreement=agreement, checks_passed=bool(low['checks_passed'] and high['checks_passed'] and agreement['checks_passed'])))
                    report['algebra'].append(dict(index=index, **algebra(y, model))); save()
                    print('identity', index, report['identities'][-1]['checks_passed'], flush=True)
            save()
        if hashes(bound) != bound:
            raise ValueError('Frozen scientific sources changed')
        for name, receipt in report['jobs'].items():
            if hashes([output/(name+'.npz')]).popitem()[1] != receipt['npz_sha256']:
                raise ValueError('Completed scientific job archive changed')
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report.update(complete=True, combined_npz_sha256=hashes([output.with_suffix('.npz')]).popitem()[1])
        report['checks_passed'] = qualification(report)
    except BaseException as failure:
        report.update(complete=False, checks_passed=False, failure=dict(type=type(failure).__name__, message=str(failure)))
        raise
    finally:
        report['wall_seconds'] = perf_counter()-clock
        save()
    print('Hybrid audit complete', report['complete'], 'passed', report['checks_passed'], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not run(args.output)['checks_passed']:
        raise RuntimeError('Scientific audit failed; evidence preserved')


if __name__ == '__main__':
    main()
