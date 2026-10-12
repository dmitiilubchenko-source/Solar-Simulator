"""Fresh source-to-restart finite-H audit; independent EIH/matrix/body Euler."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from scripts import lunar_research as research
from scripts.assess_relative_canonical import differences
from scripts.assess_rigid_pn import attitudes,convert_reference
from scripts.independent_relative_canonical import gradients,scalar,matrix_rhs
from scripts.pinned_lunar_initial import source_inputs,from_pinned_dataset
from scripts.relative_canonical import invariants,from_cartesian
from scripts.relative_canonical_checkpoint import REPRESENTATION
from solar_simulator.spin_initial import lunar_solid_equivalent_initial

POLICY = 'scripts/lunar-research-policy.json'
EXTRA_SOURCES = (POLICY,'scripts/assess_lunar_research.py','tests/test_lunar_research_audit.py',
    'tests/test_lunar_research.py','scripts/independent_relative_canonical.py',
    'scripts/independent_rigid_pn.py','scripts/independent_nbody_pn_spin.py',
    'scripts/assess_relative_canonical.py','scripts/assess_rigid_pn.py',
    'scripts/assess_nbody_pn_spin.py')
MATRIX_REPRESENTATION = 'mass-weighted-pair-Jacobi-X-r-P-pr-body-figure-spin-raw-R'


def failures(metrics,confirmations,policy):
    expected = set(policy['maximum'])|set(policy['minimum'])
    if set(metrics)!=expected or set(confirmations)!=set(policy['required_true']):
        raise ValueError('Every predeclared metric/confirmation must be reported exactly')
    if any(type(v) not in (int,float) or not np.isfinite(v) or v<0 for v in metrics.values()):
        raise ValueError('Finite nonnegative real metrics required')
    if any(type(v) is not bool for v in confirmations.values()):
        raise ValueError('Strict boolean confirmations required')
    return ([k for k,bound in policy['maximum'].items() if not metrics[k]<bound]
        +[k for k,bound in policy['minimum'].items() if not metrics[k]>bound]
        +[k for k in policy['required_true'] if not confirmations[k]])


def independent_kinematics(state,rotation,parameters,pair):
    g = gradients(np.asarray(state[:-4]),rotation,parameters.orbital.masses,
        parameters.orbital.c,parameters.figure.moments,parameters.index,pair.first,pair.second)
    _,v,w = g.reshape(3,len(pair.masses),3); v = v.copy()
    a,d = pair.fractions; centre,relative = v[pair.first].copy(),v[pair.second].copy()
    v[pair.first] = centre-d*relative; v[pair.second] = centre+a*relative
    return v,w[parameters.index],g


def boundary_controls(experiment):
    """Wrong p=m v and Newton S=I W must fail the same full-H initial derivative."""
    args = source_inputs(); units = args['units']; cp = experiment.checkpoint; p = cp.parameters
    original, _ = from_pinned_dataset(purpose='conditional-research')
    _,_,newton,profile = lunar_solid_equivalent_initial()
    r = np.array(profile['rotation']); rd = np.array(profile['rotation_derivative_per_second'])
    # Independent column identity, rather than antisymmetric Rdot R^T extraction.
    rate = sum((np.cross(r[:,i],rd[:,i]) for i in range(3)),np.zeros(3))/2*units.time_s
    matrix = attitudes(np.array([cp.state]))[0]
    wrong_p = original.copy(); wrong_p[30:60] = (np.array(p.orbital.masses)[:,None]*args['velocities']).ravel()
    wrong_s = original.copy(); wrong_s[72:75] = newton[-3:]/units.spin_kg_m2_s
    vp,_,_ = independent_kinematics(from_cartesian(wrong_p,cp.pair),matrix,p,cp.pair)
    _,ws,_ = independent_kinematics(from_cartesian(wrong_s,cp.pair),matrix,p,cp.pair)
    return dict(wrong_p_equals_mv_velocity_scaled=float((np.linalg.norm(vp-args['velocities'],axis=1)/args['velocity_scales']).max()),
        wrong_newton_spin_rate_scaled=float(np.linalg.norm(ws-rate)/args['rate_scale']))


def audit(*,output=None,work=None):
    output = ROOT/'docs/lunar-research-validation.json' if output is None else Path(output).resolve()
    work = ROOT/'.tools/rotation71' if work is None else Path(work).resolve()
    if not output.is_relative_to(ROOT) or not work.is_relative_to(ROOT):
        raise ValueError('Audit outputs must remain in the project')
    if output.exists() or work.exists(): raise FileExistsError('Preserve previous audit and jobs; use new paths')
    policy = json.loads((ROOT/POLICY).read_text('utf-8'))
    if policy['physical_mapping_certified'] is not False or policy['physical_accuracy_claimed'] is not False:
        raise ValueError('Only the predeclared conditional numerical audit is supported')
    experiment = research.create(purpose='conditional-research'); cp = experiment.checkpoint
    if cp.metadata['integration']['rtol']!=policy['production_rtol']:
        raise ValueError('Production controls differ from the frozen policy')
    args = source_inputs(); units = args['units']; params = cp.parameters; pair = cp.pair
    count = len(cp.body_names); figure = params.index; points = [i for i in range(count) if i!=figure]
    sha = lambda path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    hashes = dict(research.LOADED_SOURCE_SHA); hashes.update({p:sha(p) for p in EXTRA_SOURCES})
    work.mkdir(parents=True,exist_ok=False)
    (work/'manifest.json').write_text(json.dumps(dict(policy=policy,code_and_input_sha256=hashes),indent=2),encoding='utf-8')
    times = np.linspace(0.,policy['duration_seconds']/units.time_s,policy['samples'])
    initial = np.array(cp.initial); jobs = {}; paths = []
    def freeze():
        if hashes!={p:sha(p) for p in hashes}: raise ValueError('Audit sources changed during jobs')
    def keep(name,grid,states,representation):
        path = work/(name+'.npz')
        with path.open('xb') as stream: np.savez_compressed(stream,times=grid,states=states,representation=representation)
        paths.append(path)
    def production(name,start,grid):
        freeze(); print(name,'started',flush=True); timer = time.perf_counter()
        end, states = research.evolve(start,grid); freeze()
        jobs[name] = time.perf_counter()-timer; print(name,round(jobs[name],2),'seconds',flush=True)
        keep(name,grid,states,REPRESENTATION); return end, states
    research.save(work/'initial.json',experiment); loaded = research.load(work/'initial.json')
    end, primary = production('production',loaded,times); research.save(work/'final.json',end)
    control = cp.metadata['integration']; control.update(rtol=policy['tighter_rtol'],
        atol=(np.array(control['atol'])*policy['tighter_atol_factor']).tolist(),
        max_step=policy['tighter_max_step_seconds']/units.time_s)
    strict_experiment = research.create(purpose='conditional-research',integration=control)
    _, strict = production('tighter',strict_experiment,times)
    matrix = attitudes(initial[None,:])[0]; start = np.r_[initial[:-4],matrix.ravel()]
    ss = slice(6*count+3*figure,6*count+3*figure+3); start[ss] = matrix.T@initial[ss]
    scales = np.linalg.norm(initial[:-4].reshape(3,count,3),axis=-1); raw_refs = []; refs = []
    field = lambda t,y: matrix_rhs(t,y,params.orbital.masses,params.orbital.c,params.figure.moments,figure,pair.first,pair.second)
    for i,rtol in enumerate(policy['reference_rtols']):
        absolute = rtol*policy['reference_atol_over_rtol']*np.r_[np.repeat(scales.ravel(),3),np.ones(9)]
        for j in points: absolute[6*count+3*j:6*count+3*j+3] = policy['zero_point_spin_atol_model_units']
        if np.any(absolute<=0): raise ValueError('Positive reference atols required')
        freeze(); name = 'reference-'+str(i); print(name,'started',flush=True); timer = time.perf_counter()
        sol = solve_ivp(field,(float(times[0]),float(times[-1])),start,t_eval=times,method='RK45',rtol=rtol,
            atol=absolute,max_step=policy['reference_max_step_seconds']/units.time_s)
        if not sol.success or not np.array_equal(sol.t,times) or sol.y.shape!=(len(start),len(times)) or not np.all(np.isfinite(sol.y)):
            raise ValueError('Failed/incomplete reference '+name)
        freeze(); raw = sol.y.T; raw_refs.append(raw); refs.append(convert_reference(raw,count,figure))
        jobs[name] = time.perf_counter()-timer; keep(name,times,raw,MATRIX_REPRESENTATION)
        print(name,round(jobs[name],2),'seconds',flush=True)
    split = policy['split_sample']; middle, first = production('restart-prefix',loaded,times[:split+1])
    research.save(work/'middle.json',middle)
    with (work/'suffix-grid.npz').open('xb') as stream: np.savez_compressed(stream,times=times[split:])
    program = '''
import os,sys,numpy as np
from scripts import lunar_research as r
from scripts.relative_canonical_checkpoint import REPRESENTATION
cp=r.load(sys.argv[1])
with np.load(sys.argv[2],allow_pickle=False) as f: times=f['times'].copy()
end,states=r.evolve(cp,times);r.save(sys.argv[3],end)
with open(sys.argv[4],'xb') as f: np.savez_compressed(f,times=times,states=states,representation=REPRESENTATION,process_id=os.getpid())
print('suffix finished; pid',os.getpid(),flush=True)
'''
    freeze(); print('fresh-process suffix started',flush=True); timer = time.perf_counter()
    result = subprocess.run([sys.executable,'-X','utf8','-B','-c',program,str(work/'middle.json'),
        str(work/'suffix-grid.npz'),str(work/'resumed.json'),str(work/'suffix.npz')],cwd=ROOT,check=True,capture_output=True,text=True)
    freeze(); jobs['fresh-process-suffix'] = time.perf_counter()-timer; print(result.stdout.strip(),flush=True)
    with np.load(work/'suffix.npz',allow_pickle=False) as archive:
        if not np.array_equal(archive['times'],times[split:]) or archive['representation'].item()!=REPRESENTATION:
            raise ValueError('Changed suffix grid/representation')
        suffix = archive['states'].copy(); child_pid = int(archive['process_id'])
    if suffix.shape!=(len(times)-split,len(initial)) or not np.all(np.isfinite(suffix)):
        raise ValueError('Invalid suffix trajectory')
    joined = np.vstack([first[:-1],suffix]); keep('restarted',times,joined,REPRESENTATION); paths.append(work/'suffix.npz')
    resumed = research.load(work/'resumed.json'); restored_middle = research.load(work/'middle.json')
    spin_scale = scales[2,figure]
    delta = lambda a,ra,b,rb: differences(a,ra,b,rb,units,pair,figure,spin_scale)
    components = dict(reference=delta(primary[:,:-4],attitudes(primary),*refs[-1]),
        reference_uncertainty=delta(*refs[0],*refs[1]),tighter=delta(primary[:,:-4],attitudes(primary),strict[:,:-4],attitudes(strict)),
        restart=delta(primary[:,:-4],attitudes(primary),joined[:,:-4],attitudes(joined)))
    values = [invariants(y,params,pair) for y in primary]
    h = np.array([v[0] for v in values]); p = np.array([v[1] for v in values]); j = np.array([v[2] for v in values])
    momentum_scale = np.linalg.norm(initial[:-4].reshape(3,count,3)[1],axis=1).sum(); raw_r = np.concatenate([r[1] for r in refs])
    metrics = dict(energy_relative=float(abs(h-h[0]).max()/abs(h[0])),
        momentum_scaled=float(np.linalg.norm(p-p[0],axis=1).max()/momentum_scale),
        angular_momentum_relative=float(np.linalg.norm(j-j[0],axis=1).max()/np.linalg.norm(j[0])),
        quaternion_norm=float(abs(np.linalg.norm(primary[:,-4:],axis=1)-1).max()),
        reference_rotation_orthogonality=float(np.linalg.norm(raw_r.swapaxes(1,2)@raw_r-np.eye(3),axis=(1,2)).max()),
        reference_rotation_determinant=float(abs(np.linalg.det(raw_r)-1).max()))
    for name,part in components.items():
        for key in ['positions_m','earth_moon_position_m','figure_spin_relative','attitude_matrix']: metrics[name+'_'+key] = part[key]
    indices = np.linspace(0,len(times)-1,policy['derivative_samples'],dtype=int); diagnostics = []
    for i in indices:
        state = primary[i]; rotation = attitudes(state[None,:])[0]
        v,w,_ = independent_kinematics(state,rotation,params,pair)
        current = replace(loaded,checkpoint=replace(cp,state=tuple(state),time=float(times[i])))
        export = research.velocity_export(current)
        independent_h = float(scalar(state[:-4],rotation,params.orbital.masses,params.orbital.c,params.figure.moments,figure,pair.first,pair.second))
        diagnostics.append(dict(sample=int(i),hamiltonian_relative=abs(independent_h-h[i])/abs(h[i]),
            velocity_scaled=float((np.linalg.norm(v-np.array(export['velocity_model_units']),axis=1)/args['velocity_scales']).max()),
            rate_scaled=float(np.linalg.norm(w-np.array(export['attitude_rate_model_units']))/args['rate_scale'])))
    for key in ['hamiltonian_relative','velocity_scaled','rate_scaled']: metrics['independent_'+key] = float(max(d[key] for d in diagnostics))
    metrics.update(boundary_controls(loaded)); bitwise = lambda a,b: np.array_equal(np.array(a).view(np.uint64),np.array(b).view(np.uint64))
    confirmations = dict(source_hashes_preserved=hashes=={p:sha(p) for p in hashes},initial_bitwise=bitwise(cp.initial,loaded.checkpoint.initial),
        file_bitwise=bitwise(middle.checkpoint.state,restored_middle.checkpoint.state) and bitwise(resumed.checkpoint.state,suffix[-1]),
        suffix_start_bitwise=bitwise(first[-1],suffix[0]),metadata_preserved=cp.metadata_json==end.checkpoint.metadata_json==resumed.checkpoint.metadata_json,
        pair_and_order_preserved=cp.pair==resumed.checkpoint.pair and cp.body_names==resumed.checkpoint.body_names and cp.initial==resumed.checkpoint.initial,
        fresh_process=child_pid!=os.getpid(),receipt_preserved=loaded.receipt_json==resumed.receipt_json==experiment.receipt_json,
        point_spins_exactly_zero=all(np.array_equal(y[:,:90].reshape(-1,3,count,3)[:,2,points],np.zeros((len(y),len(points),3)))
            for y in [primary,strict,joined]+raw_refs))
    failed = failures(metrics,confirmations,policy); freeze()
    report = dict(change=71,policy=policy,metrics=metrics,components=components,confirmations=confirmations,
        derivative_diagnostics=diagnostics,job_seconds=jobs,code_and_input_sha256=hashes,
        trajectory_archives={p.relative_to(ROOT).as_posix():sha(p.relative_to(ROOT)) for p in paths},
        checkpoint_files={p.relative_to(ROOT).as_posix():sha(p.relative_to(ROOT)) for p in work.glob('*.json')},
        sample_times_seconds=(times*units.time_s).tolist(),initial_relative_state=initial.tolist(),units_SI=vars(units),
        process_ids=dict(parent=os.getpid(),suffix=child_pid),physical_mapping_certified=False,physical_accuracy_claimed=False,
        future_ephemerides_called=False,runtime_changed=False,cached_trajectories_used=False,passed=not failed,failed_criteria=failed)
    text = json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    with output.open('x',encoding='utf-8',newline='\n') as stream: stream.write(text)
    print(json.dumps(dict(metrics=metrics,confirmations=confirmations,passed=not failed,failed=failed),indent=2),flush=True)
    return not failed


if __name__=='__main__': sys.exit(0 if audit() else 1)
