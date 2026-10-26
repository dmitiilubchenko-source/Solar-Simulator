"""Strict Jacobi JSON, source-bound reference reuse and fresh-process restart."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.release_history import ui_historical_sha, verify_checkpoint_history
from scripts.assess_canonical_solar import initial_checkpoint
from scripts.assess_relative_canonical import differences
from scripts.assess_rigid_pn import attitudes,convert_reference
from scripts.relative_canonical import Pair,invariants
from scripts.relative_canonical_checkpoint import (from_cartesian_checkpoint,canonical_text,
    save,load,evolve,verify_sources,REPRESENTATION)


def verified_parent(policy):
    """Reject changed report, source/array bytes or undeclared raw representation."""
    sha = lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    if sha(policy['parent_report'])!=policy['parent_report_sha256']:
        raise ValueError('Changed immutable relative audit')
    report = json.loads((ROOT/policy['parent_report']).read_text(encoding='utf-8'))
    if (report['passed'] is not True or report['change']!=62
            or report['physical_lunar_mapping_certified'] is not False
            or report['policy']!=json.loads((ROOT/'scripts/relative-canonical-policy.json').read_text(encoding='utf-8'))):
        raise ValueError('Incompatible parent scientific contract')
    for section in ['code_and_input_sha256','trajectory_archives']:
        for p,h in report[section].items():
            path = (ROOT/p).resolve()
            if (not path.is_relative_to(ROOT) or
                    (ui_historical_sha(ROOT,p,h) if section=='code_and_input_sha256' else sha(p))!=h):
                raise ValueError('Changed parent source/array: '+p)
    arrays = {}
    for name in ['production','tighter','reference-0','reference-1']:
        path = '.tools/rotation62/'+name+'.npz'
        if path not in report['trajectory_archives']:raise ValueError('Missing declared parent archive')
        with np.load(ROOT/path,allow_pickle=False) as archive:
            representation = archive['representation'].item()
            expected = REPRESENTATION if name in ['production','tighter'] else 'mass-weighted-pair-Jacobi-X-r-P-pr-body-figure-spin-raw-R'
            if representation!=expected:raise ValueError('Changed parent raw representation')
            arrays[name] = dict(times=archive['times'].copy(),states=archive['states'].copy())
    return report,arrays


def initial_relative(policy, parent):
    old_policy = json.loads((ROOT/parent['policy']['input_policy']).read_text(encoding='utf-8'))
    old,units,names = initial_checkpoint(old_policy);count = len(names)
    if (policy['physical_lunar_mapping_certified'] is not False or policy['physical_accuracy_claimed'] is not False
            or policy['duration_seconds']!=parent['policy']['duration_seconds'] or policy['samples']!=parent['policy']['samples']
            or vars(units)!=parent['units_SI'] or not np.array_equal(np.array(old.initial).view(np.uint64),
                np.array(parent['initial_cartesian_state']).view(np.uint64))):
        raise ValueError('Incompatible initial/units/physical contract')
    pair = Pair(old.parameters.orbital.masses,*parent['policy']['pair']);ma,md = pair.masses[pair.first],pair.masses[pair.second]
    control = old.metadata['integration'];atol = np.array(control['atol']);p = parent['policy']
    atol[:3*count] = p['position_atol_m']/units.length_m
    atol[3*count+3*pair.first:3*count+3*pair.first+3] = (ma+md)*p['momentum_atol_equivalent_velocity_m_s']/units.velocity_m_s
    atol[3*count+3*pair.second:3*count+3*pair.second+3] = ma*md/(ma+md)*p['momentum_atol_equivalent_velocity_m_s']/units.velocity_m_s
    control.update(rtol=p['production_rtol'],atol=atol.tolist(),max_step=p['max_step_seconds']/units.time_s)
    cp = from_cartesian_checkpoint(old,pair,names,integration=control)
    if not np.array_equal(np.array(cp.initial).view(np.uint64),np.array(parent['initial_state']).view(np.uint64)):
        raise ValueError('Initial Jacobi state differs bitwise')
    meta = cp.metadata;recorded = {s['path'] for s in meta['provenance']['sources']}
    extra = {**parent['code_and_input_sha256'],**parent['trajectory_archives']}
    for path in [policy['parent_report'],'scripts/relative-canonical-checkpoint-policy.json',
        'scripts/assess_relative_canonical_checkpoint.py','scripts/resume_relative_canonical.py',
        'tests/test_relative_canonical_checkpoint.py','tests/test_relative_canonical_checkpoint_audit.py']:
        extra[path] = hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    for path,h in extra.items():
        if path not in recorded:meta['provenance']['sources'].append(dict(path=path,sha256=h))
    cp = replace(cp,metadata_json=canonical_text(meta));verify_sources(cp,ROOT)
    return cp,units,names


def historical_initial_relative(policy, parent):
    """Read checkpoint63 unchanged; no rebinding or current-solver conversion."""
    path = ROOT/'.tools/rotation63/initial.json'
    if hashlib.sha256(path.read_bytes()).hexdigest() != '02ee4efa985402898568d13e41050bfad6da5717e0148ab08a3f6a4e1af20623':
        raise ValueError('Changed immutable historical relative initial')
    cp = load(path);verify_checkpoint_history(cp,ROOT)
    old_policy = json.loads((ROOT/parent['policy']['input_policy']).read_text(encoding='utf-8'))
    old,units,names = initial_checkpoint(old_policy)
    from scripts.relative_canonical import from_cartesian
    if (policy['physical_lunar_mapping_certified'] is not False or policy['physical_accuracy_claimed'] is not False
            or policy['duration_seconds']!=parent['policy']['duration_seconds'] or policy['samples']!=parent['policy']['samples']
            or vars(units)!=parent['units_SI'] or cp.parameters!=old.parameters
            or cp.body_names!=tuple(names) or (cp.pair.first,cp.pair.second)!=tuple(parent['policy']['pair'])
            or not np.array_equal(np.array(old.initial).view(np.uint64),np.array(parent['initial_cartesian_state']).view(np.uint64))
            or not np.array_equal(np.array(cp.initial).view(np.uint64),np.array(parent['initial_state']).view(np.uint64))
            or not np.array_equal(from_cartesian(old.initial,cp.pair).view(np.uint64),np.array(cp.initial).view(np.uint64))):
        raise ValueError('Incompatible historical initial/units/physical contract')
    control = old.metadata['integration'];count = len(names);pair = cp.pair;p = parent['policy']
    ma,md = pair.masses[pair.first],pair.masses[pair.second];atol = np.array(control['atol'])
    atol[:3*count] = p['position_atol_m']/units.length_m
    atol[3*count+3*pair.first:3*count+3*pair.first+3] = (ma+md)*p['momentum_atol_equivalent_velocity_m_s']/units.velocity_m_s
    atol[3*count+3*pair.second:3*count+3*pair.second+3] = ma*md/(ma+md)*p['momentum_atol_equivalent_velocity_m_s']/units.velocity_m_s
    control.update(rtol=p['production_rtol'],atol=atol.tolist(),max_step=p['max_step_seconds']/units.time_s)
    if cp.metadata['integration']!=control:
        raise ValueError('Changed historical relative solver controls')
    return cp,units,names


def audit():
    output = ROOT/'docs/relative-canonical-checkpoint-validation.json'
    if output.exists():raise FileExistsError('Preserve original relative checkpoint audit')
    policy = json.loads((ROOT/'scripts/relative-canonical-checkpoint-policy.json').read_text(encoding='utf-8'))
    parent,arrays = verified_parent(policy);cp,units,names = initial_relative(policy,parent)
    count = len(names);params = cp.parameters;figure = params.index;times = np.linspace(0.,policy['duration_seconds']/units.time_s,policy['samples'])
    for name,archive in arrays.items():
        size = 9*count+(4 if name in ['production','tighter'] else 9)
        states = archive['states']
        if (states.shape!=(len(times),size) or not np.array_equal(archive['times'],times)
                or not np.all(np.isfinite(states))):raise ValueError('Invalid parent grid/array')
        if name in ['production','tighter']:
            if not np.array_equal(states[0].view(np.uint64),np.array(cp.initial).view(np.uint64)):
                raise ValueError('Parent initial array differs bitwise')
    work = ROOT/'.tools/rotation63';jobs = {};paths = []
    def keep(name,grid,states):
        path = work/(name+'.npz')
        with path.open('xb') as f:np.savez_compressed(f,times=grid,states=states,representation=REPRESENTATION)
        paths.append(path)
    def production(name,start,grid):
        print(name,'started',flush=True);clock = time.perf_counter();end,states = evolve(start,grid,source_root=ROOT)
        jobs[name] = time.perf_counter()-clock;print(name,round(jobs[name],2),'seconds',flush=True)
        return end,states
    save(work/'initial.json',cp);loaded_initial = load(work/'initial.json')
    end,primary = production('production',loaded_initial,times);keep('production',times,primary)
    split = policy['split_sample'];middle,first = production('restart-prefix',loaded_initial,times[:split+1])
    save(work/'middle.json',middle);save(work/'full-final.json',end)
    with (work/'suffix-grid.npz').open('xb') as f:np.savez_compressed(f,times=times[split:])
    print('fresh-process suffix started',flush=True);clock = time.perf_counter()
    process = subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/resume_relative_canonical.py'),
        '--input',str(work/'middle.json'),'--times',str(work/'suffix-grid.npz'),
        '--checkpoint-output',str(work/'resumed-final.json'),'--trajectory-output',str(work/'suffix.npz')],
        cwd=ROOT,capture_output=True,text=True,check=True)
    jobs['fresh-process-suffix'] = time.perf_counter()-clock;print(process.stdout.strip(),flush=True)
    with np.load(work/'suffix.npz',allow_pickle=False) as a:
        if not np.array_equal(a['times'],times[split:]) or a['representation'].item()!=REPRESENTATION:raise ValueError('Invalid subprocess array')
        last = a['states'].copy();child_pid = int(a['process_id'])
    joined = np.vstack([first[:-1],last]);keep('restarted',times,joined);paths.append(work/'suffix.npz')
    final = load(work/'resumed-final.json');loaded_middle = load(work/'middle.json')
    if last.shape!=(len(times)-split,len(cp.state)) or not np.all(np.isfinite(last)):raise ValueError('Invalid suffix states')
    refs = [convert_reference(arrays[f'reference-{i}']['states'],count,figure) for i in range(2)]
    spin = np.linalg.norm(np.array(cp.initial[:-4]).reshape(3,count,3)[2,figure])
    delta = lambda a,ra,b,rb:differences(a,ra,b,rb,units,cp.pair,figure,spin)
    components = dict(reference=delta(primary[:,:-4],attitudes(primary),*refs[-1]),
        reference_uncertainty=delta(*refs[0],*refs[1]),
        tighter=delta(primary[:,:-4],attitudes(primary),arrays['tighter']['states'][:,:-4],attitudes(arrays['tighter']['states'])),
        restart=delta(primary[:,:-4],attitudes(primary),joined[:,:-4],attitudes(joined)))
    values = [invariants(y,params,cp.pair) for y in primary];h = np.array([v[0] for v in values]);p = np.array([v[1] for v in values]);j = np.array([v[2] for v in values])
    momentum_scale = np.linalg.norm(np.array(parent['initial_cartesian_state'][:-4]).reshape(3,count,3)[1],axis=1).sum()
    raw_r = np.concatenate([ref[1] for ref in refs])
    metrics = dict(energy_relative=float(abs(h-h[0]).max()/abs(h[0])),momentum_scaled=float(np.linalg.norm(p-p[0],axis=1).max()/momentum_scale),
        angular_momentum_relative=float(np.linalg.norm(j-j[0],axis=1).max()/np.linalg.norm(j[0])),
        quaternion_norm=float(abs(np.linalg.norm(primary[:,-4:],axis=1)-1).max()),
        reference_rotation_orthogonality=float(np.linalg.norm(np.swapaxes(raw_r,1,2)@raw_r-np.eye(3),axis=(1,2)).max()),
        reference_rotation_determinant=float(abs(np.linalg.det(raw_r)-1).max()))
    for name,result in components.items():
        for key in ['positions_m','earth_moon_position_m','figure_spin_relative','attitude_matrix']:metrics[name+'_'+key] = result[key]
    hashes = {s['path']:s['sha256'] for s in cp.metadata['provenance']['sources']};sha = lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    bitwise = lambda a,b:np.array_equal(np.array(a).view(np.uint64),np.array(b).view(np.uint64))
    points = [i for i in range(count) if i!=figure]
    confirmations = dict(initial_bitwise=bitwise(cp.initial,loaded_initial.initial),
        file_bitwise=bitwise(middle.state,loaded_middle.state) and bitwise(final.state,last[-1]),
        suffix_start_bitwise=bitwise(first[-1],last[0]),metadata_preserved=cp.metadata_json==end.metadata_json==final.metadata_json,
        pair_and_order_preserved=cp.pair==final.pair and cp.body_names==final.body_names and cp.initial==final.initial,
        source_hashes_preserved=hashes=={p:sha(p) for p in hashes},fresh_process=child_pid!=os.getpid(),
        production_matches_parent_bitwise=bitwise(primary,arrays['production']['states']),
        point_spins_exactly_zero=all(np.array_equal(y[:,:9*count].reshape(-1,3,count,3)[:,2,points],np.zeros((len(y),len(points),3)))
            for y in [primary,joined]+[arrays[f'reference-{i}']['states'] for i in range(2)]))
    failed = [k for k,v in policy['criteria'].items() if not metrics[k]<v]+[k for k in policy['required_true'] if not confirmations[k]]
    report = dict(change=63,policy=policy,metrics=metrics,components=components,confirmations=confirmations,job_seconds=jobs,
        parent_reference_reused_after_SHA_contract_checks=True,code_and_input_sha256=hashes,
        trajectory_archives={p.relative_to(ROOT).as_posix():sha(p.relative_to(ROOT)) for p in paths},
        checkpoint_files={p.relative_to(ROOT).as_posix():sha(p.relative_to(ROOT)) for p in work.glob('*.json') if p.name!='before.json'},
        process_ids=dict(parent=os.getpid(),suffix=child_pid),physical_lunar_mapping_certified=False,
        physical_accuracy_claimed=False,future_ephemerides_called=False,runtime_changed=False,passed=not failed,failed_criteria=failed)
    with output.open('x',encoding='utf-8') as f:f.write(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(metrics=metrics,confirmations=confirmations,passed=not failed,failed=failed),indent=2),flush=True)
    return not failed


if __name__=='__main__':sys.exit(0 if audit() else 1)
