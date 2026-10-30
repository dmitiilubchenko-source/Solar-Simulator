"""Successor375 assessment: fresh science separate from historical compatibility.

Uses existing375 metric/gates; independent scalar math.dist/fsum reductions
verify saved arrays. This is not an independent physical theory or external review.
"""
import argparse
import json
from math import dist, fsum, sqrt, isclose
from pathlib import Path
import sys


def scalar_errors(actual, reference):
    pairs = zip(actual.reshape(-1, 6), reference.reshape(-1, 6))
    rows = [(dist(a[:3], b[:3]), dist(a[3:], b[3:])) for a, b in pairs]
    return dict(position_metres=max(x[0] for x in rows), velocity_m_per_s=max(x[1] for x in rows))


def scalar_invariants(values, masses, names, figures, G, c):
    """SI scalar Noether E/P/L through1PN plus fixed-axis Newton J2 energy.

    E is J, canonical P kg m/s, L kg m²/s. Fixed-axis fields do not conserve
    total orbital L. O(c^-4) and mixed PN-figure terms remain omitted.
    """
    p, v = [list(map(float, x[:3])) for x in values], [list(map(float, x[3:])) for x in values]
    m = list(map(float, masses)); n = len(m)
    dot = lambda a, b: fsum(x*y for x, y in zip(a, b))
    speed = [dot(x, x) for x in v]
    u, pairs, energy, canonical = [], [], [], []
    for i in range(n):
        terms, uv, pv = [], [], [[] for _ in range(3)]
        for j in range(n):
            if i == j:
                continue
            r = [p[i][k]-p[j][k] for k in range(3)]
            radius = sqrt(dot(r, r)); axis = [x/radius for x in r]
            potential = G*m[j]/radius
            pair = m[i]*potential
            uv.append(potential)
            terms.append(pair*(3*(speed[i]+speed[j])-7*dot(v[i], v[j])-dot(axis, v[i])*dot(axis, v[j])))
            for k in range(3):
                pv[k].append(pair*(6*v[i][k]-7*v[j][k]-axis[k]*dot(axis, v[j]))/(2*c*c))
        ui = fsum(uv)
        u.append(ui); pairs.extend(terms)
        energy.append(.5*m[i]*(speed[i]-ui))
        canonical.append([m[i]*v[i][k]*(1+.5*speed[i]/(c*c))+fsum(pv[k]) for k in range(3)])
    E = fsum(energy)+(fsum(.375*m[i]*speed[i]**2+.5*m[i]*u[i]**2 for i in range(n))+.25*fsum(pairs))/(c*c)
    quadrupoles = []
    for figure in figures:
        i = names.index(figure['body'])
        # FixedJ2 normalizes the supplied axis; keep the same geometric contract.
        axis = figure['axis']; length = sqrt(dot(axis, axis)); axis = [x/length for x in axis]
        for j in range(n):
            if i == j:
                continue
            r = [p[j][k]-p[i][k] for k in range(3)]; radius = sqrt(dot(r, r))
            z = dot(axis, r)/radius
            quadrupoles.append(G*m[i]*m[j]*figure['coefficient']*figure['reference_radius']**2*(3*z*z-1)/(2*radius**3))
    E += fsum(quadrupoles)
    P = [fsum(x[k] for x in canonical) for k in range(3)]
    L = [fsum(p[i][(k+1)%3]*canonical[i][(k+2)%3]-p[i][(k+2)%3]*canonical[i][(k+1)%3] for i in range(n)) for k in range(3)]
    return E, P, L


def validate_archive(path, digest, shapes, sha):
    import numpy as np
    if sha(path) != digest:
        raise ValueError('Changed saved array SHA')
    with np.load(path, allow_pickle=False) as data:
        if not set(shapes) <= set(data.files):
            raise ValueError('Incomplete saved array archive')
        for key, shape in shapes.items():
            if data[key].shape != tuple(shape) or not np.isfinite(data[key]).all():
                raise ValueError('Incomplete or nonfinite saved states: '+key)
        return {k: data[k].copy() for k in data.files}


def assess(candidate, freeze_path, protocol_path, work, output):
    sys.path[:0] = [str(candidate/'src'), str(candidate)]
    from scripts import qualify_current_runtime375 as q, assess_current_runtime375 as old
    from scripts.assess_sandbox_models import load_inputs
    from scripts.assess_dense_jpl import validate_reference, residuals
    from scripts.fetch_ephemerides import parse_result
    from solar_simulator.ephemerides import RESOLVED_IDS
    from solar_simulator.simulation import G
    from solar_simulator.relativity import C
    from solar_simulator.diagnostics import model_invariants
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    import numpy as np
    import importlib.util
    tool = Path(__file__).resolve().with_name('qualify_annual385.py')
    spec = importlib.util.spec_from_file_location('_annual385', tool)
    wrapper = importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
    frozen = wrapper.freeze_check(candidate, freeze_path, protocol_path)
    if output.exists():
        raise FileExistsError('Preserve prior assessment')
    p = q.protocol(protocol_path, frozen['protocol_SHA256']); criteria = p['criteria']
    q.verify_inputs(p)
    current, a = old.load_job('current', p, work=work, protocol_sha=frozen['protocol_SHA256'])
    ref = json.loads((work/'run-reference/receipt.json').read_bytes())
    if not ref['solver_executed'] or ref['protocol_sha256'] != frozen['protocol_SHA256']:
        raise ValueError('Missing fresh reference provenance')
    if current['environment'] != ref['environment'] or current['environment'] != p['candidate_environment']:
        raise ValueError('Mismatched actual numerical environments')
    for kind in ('current', 'reference'):
        trace = json.loads((work/(kind+'-trace.json')).read_bytes())
        if not trace['complete'] or not trace['source_environment_unchanged'] or trace['freeze_SHA256'] != q.sha(freeze_path):
            raise ValueError('Incomplete acquisition/changed freeze')
    for name, digest in ref['source_sha256'].items():
        if q.sha(candidate/name) != digest:
            raise ValueError('Changed reference source: '+name)
    oracle = work/'run-reference/oracle'
    if (q.sha(oracle/'scripts/validation/eih_scalar.rs') != ref['oracle_source_sha256'] or
        q.sha(oracle/'scripts/independent_eih_rust.py') != ref['loader_sha256'] or
        q.sha(oracle/'.tools'/('independent-eih-'+ref['oracle_source_sha256'][:16]+'.dll')) != ref['oracle_binary_sha256']):
        raise ValueError('Changed fresh reference source/compiled oracle')
    initial, origin, _, _, _ = load_inputs(); names = [b.name for b in initial]
    e, m = names.index('Earth'), names.index('Moon')
    times = (np.asarray(p['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    holdout = np.asarray(p['holdout_times_seconds']); refs = {}; ref_checks = {}
    from scripts.assess_sandbox_planets import states
    if not old.bits(a['initial'], states(initial)) or not old.bits(a['masses'], np.array([b.mass for b in initial])):
        raise ValueError('Actual initial state/masses changed')
    for key, grid in [('annual', times), ('holdout', holdout)]:
        if not old.bits(a['times' if key=='annual' else 'holdout_times'], grid):
            raise ValueError('Changed epoch grid')
        file = work/'run-reference'/(key+'.npz')
        data = validate_archive(file, ref['results'][key]['output_sha256'],
            {'times':(len(grid),), 'level_0':(len(grid),10,6), 'level_1':(len(grid),10,6)}, q.sha)
        if not old.bits(data['times'], grid):
            raise ValueError('Changed reference epoch grid')
        ref_checks[key] = old.numerical(data['level_0'], data['level_1'], names, criteria)
        refs[key] = data['level_1']
        all_error = scalar_errors(data['level_0'], data['level_1'])
        em_error = scalar_errors(data['level_0'][:,m]-data['level_0'][:,e], data['level_1'][:,m]-data['level_1'][:,e])
        ref_checks[key].update(all_bodies_independent=all_error, earth_moon_independent=em_error)
    dense = json.loads((candidate/'docs/qualification-grid-reference.json').read_bytes())
    expected = validate_reference(dense, origin, names, RESOLVED_IDS, p['epochs_jd_tdb'])
    raw_count = 0
    for body in dense['bodies']:
        raw, offset = [], 0
        for request in body['requests']:
            path = candidate/f".tools/qualification144/jpl-batches/horizons-{body['id']}-{offset:03d}.json"
            raw.extend(parse_result(json.loads(path.read_bytes()), body['id'], request['epochs_jd_tdb']))
            offset += len(request['epochs_jd_tdb']); raw_count += 1
        if raw != body['states']:
            raise ValueError('JPL raw responses do not match pinned reference')
    overlap = scalar_errors(a['initial'], expected[0])
    if overlap['position_metres'] > .01 or overlap['velocity_m_per_s'] > 1e-8:
        raise ValueError('JPL initial overlap SI/frame/time failed')
    gates, results, audit = {}, {}, {}
    for key, row in ref_checks.items():
        gates['reference_'+key] = (row['all_bodies_independent']['position_metres'] < criteria['reference_position_m'] and row['earth_moon_independent']['position_metres'] < criteria['reference_earth_moon_position_m'])
    E0, P0, L0 = scalar_invariants(a['initial'], a['masses'], names, p['settings']['figures'], G, C)
    pscale = fsum(float(b.mass)*b.velocity.magnitude() for b in initial)
    for backend in ('python', 'rust'):
        for suffix in ('strict20', 'strict10', 'standard20', 'holdout20'):
            key = backend+'_'+suffix; job = current['jobs'][key]
            grid = holdout if suffix=='holdout20' else times
            value = a[key+'_values']; packet = 10 if suffix=='strict10' else 20
            if value.shape != (len(grid),10,6) or not np.isfinite(value).all() or not old.bits(value[0], a['initial']) and grid[0]==0:
                raise ValueError('Incomplete trajectory/initial state')
            if not old.bits(a[key+'_packets'], old.packet_grid(grid, packet)):
                raise ValueError('Actual packet grid changed')
            settings = dict(p['settings'], backend=backend, rtol=1e-13 if suffix=='standard20' else 3e-14)
            if job['settings'] != settings or job['rtol'] != settings['rtol'] or job['packet_max_steps'] != packet:
                raise ValueError('Actual numerical settings changed')
            if (backend=='rust') != (job['native_force_calls'] > 0):
                raise ValueError('Missing actual force backend calls')
            acquisition = json.loads((work/'current-trace.json').read_bytes())['rows'][key]
            if acquisition['solver_calls'] <= 0 or acquisition['nfev'] <= 0 or job['native_force_calls'] != (acquisition['nfev'] if backend=='rust' else 0):
                raise ValueError('Actual production RHS/native calls differ')
            if suffix=='strict20':
                if not old.bits(a[key+'_resumed_values'], value[len(grid)//2:]):
                    raise ValueError('Saved-state resume arrays differ')
                from solar_simulator.storage import load
                middle = load(work/'run-current'/(key+'-middle.json'))
                if middle.time != grid[len(grid)//2] or not old.bits(states(middle.bodies),value[len(grid)//2]):
                    raise ValueError('Persisted middle checkpoint does not match trajectory')
            reference = refs['holdout' if suffix=='holdout20' else 'annual']
            row = old.numerical(value, reference, names, criteria)
            independent = dict(per_body={name:scalar_errors(value[:,i],reference[:,i]) for i,name in enumerate(names)},
                               earth_moon=scalar_errors(value[:,m]-value[:,e],reference[:,m]-reference[:,e]))
            for name in names+['earth_moon']:
                x = row['earth_moon'] if name=='earth_moon' else row['per_body'][name]
                y = independent['earth_moon'] if name=='earth_moon' else independent['per_body'][name]
                if any(not isclose(x[k],y[k],rel_tol=4e-15,abs_tol=1e-18) for k in x):
                    raise ValueError('Independent scalar reduction mismatch')
            energies, momentum, angular, discrepancies = [], [], [], []
            runtime_figures = q.strict_seed(backend).settings.figures
            for state in value:
                E, P, L = scalar_invariants(state,a['masses'],names,settings['figures'],G,C)
                bodies = [Body(name,float(mass),Vector3(*s[:3]),Vector3(*s[3:])) for name,mass,s in zip(names,a['masses'],state)]
                production_E = model_invariants(bodies,settings['physics'],runtime_figures)[0]
                discrepancies.append(abs(E-production_E)/abs(E0))
                energies.append(abs(E-E0)/abs(E0)); momentum.append(dist(P,P0)/pscale); angular.append(dist(L,L0)/sqrt(fsum(x*x for x in L0)))
            row.update(energy_residual=job['relative_energy_residual'],independent_energy_residual=max(energies),
                independent_P_scaled=max(momentum),orbital_L_change=max(angular),L_conservation_expected=False,
                scalar_vs_runtime_energy_discrepancy=max(discrepancies))
            if max(discrepancies)>1e-13:
                raise ValueError('Independent scalar invariant disagreement')
            row['energy_check_passed'] = row['energy_residual']<criteria['energy_residual'] and max(energies)<criteria['energy_residual']
            if suffix!='holdout20':
                row['jpl'] = residuals(value,expected,names,p['epochs_jd_tdb'])
                # Independently check every body and relative JPL max, not ready flags.
                independent['jpl_per_body']={name:scalar_errors(value[:,i],expected[:,i]) for i,name in enumerate(names)}
                independent['jpl_earth_moon']=scalar_errors(value[:,m]-value[:,e],expected[:,m]-expected[:,e])
                direct_jpl = all(x['position_metres']<criteria['jpl_per_body_position_m'] for x in independent['jpl_per_body'].values()) and independent['jpl_earth_moon']['position_metres']<criteria['jpl_earth_moon_position_m']
                if direct_jpl != row['jpl']['physical_goals_passed']:
                    raise ValueError('Independent JPL gate mismatch')
                for name in names+['earth_moon']:
                    x = row['jpl']['moon_relative_jpl'] if name=='earth_moon' else row['jpl']['jpl_residuals'][name]
                    y = independent['jpl_earth_moon'] if name=='earth_moon' else independent['jpl_per_body'][name]
                    if any(not isclose(x[k],y[k],rel_tol=4e-15,abs_tol=1e-18) for k in y):
                        raise ValueError('Independent JPL metric mismatch')
            results[key], audit[key] = row, independent
            if suffix!='standard20':
                gates[key] = bool(row['checks_passed'] and row['energy_check_passed'] and (suffix=='holdout20' or direct_jpl))
        for kind,suffix in [('tolerance','standard20'),('packet','strict10')]:
            row = old.sensitivity(a[backend+'_strict20_values'],a[backend+'_'+suffix+'_values'],names,criteria)
            results[backend+'_'+kind]=row; gates[backend+'_'+kind]=bool(row['checks_passed'])
    gates['same_packet_restart'] = all(current['jobs'][b+'_strict20']['checkpoint_continue_exact'] for b in ('python','rust'))
    for row in current['sandbox']:
        gates['sandbox_'+row['backend']+'_'+row['name']] = bool(row['checks_passed'] and row['file_branch_roundtrip'] and row['file_continue_exact'] and row['parent_file_preserved'])
    wrapper.freeze_check(candidate,freeze_path,protocol_path)
    out = dict(stage=385,candidate_commit=frozen['candidate_commit'],freeze_SHA256=q.sha(freeze_path),protocol_SHA256=q.sha(protocol_path),
        source_environment_unchanged=True,results=results,reference=ref_checks,independent_saved_array_audit=audit,
        gates=gates,failed_criteria=[k for k,v in gates.items() if not v],annual_scientific_qualified=all(gates.values()),
        compatibility=dict(status='UNRESOLVED',original_accepted032_environment_reexecuted=False,byte_exact_gate_satisfied=False,
            reason='Original375 environment had unset numerical thread variables. New stage deliberately freezes1; accepted032 was not rerun in a substituted environment.'),
        raw_JPL_responses_verified=raw_count,initial_JPL_overlap=overlap,executed_jobs=current['jobs'],sandbox=current['sandbox'],
        limitations=p['limitations']+['Scalar audit shares equations/constants and binary64; not external review. FixedJ2 orbital L is not conserved; mixedPN-figure and higher PN terms omitted. Complete release not qualified.'])
    q.write_json(output,out)
    print(json.dumps(dict(annual_scientific_qualified=out['annual_scientific_qualified'],failed=out['failed_criteria'],compatibility=out['compatibility']['status'])))
    return out


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('candidate','freeze','protocol','work','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=assess(args.candidate,args.freeze,args.protocol,args.work,args.output)
    raise SystemExit(0 if result['annual_scientific_qualified'] else 1)
