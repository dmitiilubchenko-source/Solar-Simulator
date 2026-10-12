"""Predeclared 32-day conditional Moon audit, no future ephemeris or fitting."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.lunar_canonical_diagnostic import initial_checkpoint, differences
from scripts.canonical_checkpoint import canonical_text, evolve, save, load
from scripts.independent_rigid_pn import matrix_rhs
from scripts.assess_rigid_pn import attitudes, convert_reference
from scripts.rigid_pn_model import invariants


def audit():
    output=ROOT/'docs/lunar-canonical-validation.json'
    if output.exists():raise FileExistsError('Preserve conditional lunar audit')
    policy=json.loads((ROOT/'scripts/lunar-canonical-policy.json').read_text(encoding='utf-8'))
    cp,units,initial_info=initial_checkpoint(policy);params=cp.parameters
    sources={r['path']:r['sha256'] for r in cp.metadata['provenance']['sources']}
    sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    work=ROOT/'.tools/rotation60';work.mkdir(exist_ok=True)
    times=np.linspace(0.,policy['duration_seconds']/units.time_s,policy['samples'])
    initial=np.array(cp.state);spin_scale=np.linalg.norm(initial[:-4].reshape(3,3,3)[2,2])
    job_seconds={};saved_arrays={}
    def keep(name,states):
        path=work/(name+'.npz')
        with path.open('xb') as stream:np.savez_compressed(stream,times=times,states=states)
        saved_arrays[path.relative_to(ROOT).as_posix()]=sha(path.relative_to(ROOT))
    save(work/'initial.json',cp)
    def production(name,start,grid):
        print(name,'started',flush=True);timer=time.perf_counter()
        end,states=evolve(start,grid,source_root=ROOT)
        job_seconds[name]=time.perf_counter()-timer
        print(name,round(job_seconds[name],2),'seconds',flush=True)
        return end,states
    endpoint,primary=production('production',cp,times);keep('production',primary)
    strict_meta=cp.metadata;strict_meta['integration'].update(rtol=policy['tighter_rtol'],
        atol=(np.array(strict_meta['integration']['atol'])*policy['tighter_atol_factor']).tolist(),
        max_step=policy['tighter_max_step_seconds']/units.time_s)
    strict_start=replace(cp,metadata_json=canonical_text(strict_meta))
    _,strict=production('tighter',strict_start,times);keep('tighter',strict)
    matrix=Rotation.from_quat(np.roll(initial[-4:],-1)).as_matrix()
    matrix_start=np.r_[initial[:-4],matrix.ravel()]
    matrix_start[24:27]=matrix.T@initial[24:27]
    scales=np.linalg.norm(initial[:-4].reshape(3,3,3),axis=-1)
    # Nonzero x/p/figure spin use their scales; zero ideal point-spins get
    # a declared absolute atol, not an invented spin magnitude/epsilon.
    references=[];raw_refs=[]
    for i,rtol in enumerate(policy['reference_rtols']):
        atol=rtol*policy['reference_atol_over_rtol']*np.r_[np.repeat(scales.ravel(),3),np.ones(9)]
        atol[18:24]=policy['zero_point_spin_atol_model_units']
        name=f'reference-{i}';print(name,'started',flush=True);timer=time.perf_counter()
        result=solve_ivp(lambda t,y:matrix_rhs(t,y,params.orbital.masses,params.orbital.c,params.figure.moments,2),
            (0.,float(times[-1])),matrix_start,t_eval=times,method='RK45',rtol=rtol,atol=atol,
            max_step=policy['max_step_seconds']/units.time_s)
        if (not result.success or result.y.shape!=(36,len(times))
                or not np.array_equal(result.t,times) or not np.all(np.isfinite(result.y))):
            raise ValueError(f'Invalid independent integration {name}')
        raw=result.y.T;job_seconds[name]=time.perf_counter()-timer;keep(name,raw)
        raw_refs.append(raw);references.append(convert_reference(raw,3,2))
        print(name,round(job_seconds[name],2),'seconds',flush=True)
    split=policy['split_sample'];middle,first=production('restart-prefix',cp,times[:split+1])
    save(work/'middle.json',middle);restored=load(work/'middle.json')
    final,last=production('restart-suffix',restored,times[split:]);restarted=np.vstack([first[:-1],last]);keep('restarted',restarted)
    rotations=attitudes(primary)
    reference=differences(primary[:,:-4],rotations,*references[-1],units,spin_scale)
    uncertainty=differences(*references[0],*references[1],units,spin_scale)
    sensitivity=differences(primary[:,:-4],rotations,strict[:,:-4],attitudes(strict),units,spin_scale)
    restart=differences(primary[:,:-4],rotations,restarted[:,:-4],attitudes(restarted),units,spin_scale)
    values=[invariants(y,params) for y in primary]
    h=np.array([v[0] for v in values]);p=np.array([v[1] for v in values]);j=np.array([v[2] for v in values])
    if min(abs(h[0]),np.linalg.norm(j[0]),scales[1].sum())<=0:raise ValueError('Degenerate invariant scales')
    raw_r=np.concatenate([r[1] for r in references])
    orthogonality=np.linalg.norm(np.swapaxes(raw_r,1,2)@raw_r-np.eye(3),axis=(1,2)).max()
    determinant=np.max(abs(np.linalg.det(raw_r)-1))
    metrics=dict(energy_relative=float(np.max(abs(h-h[0]))/abs(h[0])),
        momentum_scaled=float(np.linalg.norm(p-p[0],axis=1).max()/scales[1].sum()),
        angular_momentum_relative=float(np.linalg.norm(j-j[0],axis=1).max()/np.linalg.norm(j[0])),
        quaternion_norm=float(np.max(abs(np.linalg.norm(primary[:,-4:],axis=1)-1))),
        reference_rotation_orthogonality=float(orthogonality),reference_rotation_determinant=float(determinant),
        initial_velocity_residual=initial_info['inversion']['velocity_residual'],
        initial_attitude_rate_residual=initial_info['inversion']['attitude_rate_residual'])
    for prefix,check in [('reference',reference),('reference_uncertainty',uncertainty),('tighter',sensitivity),('restart',restart)]:
        for key in ['positions_m','earth_moon_position_m','figure_spin_relative','attitude_matrix']:
            metrics[prefix+'_'+key]=check[key]
    points_zero=all(np.array_equal(states[:,:27].reshape(-1,3,3,3)[:,2,:2],np.zeros((len(states),2,3)))
                    for states in [primary,strict,restarted]+raw_refs)
    confirmations=dict(point_spins_exactly_zero=points_zero,
        checkpoint_bitwise=np.array_equal(np.array(middle.state).view(np.uint64),np.array(restored.state).view(np.uint64)),
        metadata_preserved=cp.metadata_json==endpoint.metadata_json==restored.metadata_json==final.metadata_json,
        source_hashes_preserved=sources=={p:sha(p) for p in sources})
    failed=[k for k,limit in policy['criteria'].items() if not metrics[k]<limit]
    failed += [k for k in policy['required_true'] if not confirmations[k]]
    report=dict(change=60,policy=policy,initial_info=initial_info,initial_state=initial.tolist(),
        units_SI=vars(units),time_unit_s=units.time_s,sample_times_seconds=(times*units.time_s).tolist(),
        metrics=metrics,confirmations=confirmations,reference_components=reference,
        reference_uncertainty_components=uncertainty,tighter_components=sensitivity,restart_components=restart,
        job_seconds=job_seconds,code_and_input_sha256=sources,trajectory_archives=saved_arrays,
        checkpoint_files={p.relative_to(ROOT).as_posix():sha(p.relative_to(ROOT)) for p in work.glob('*.json') if p.name!='before.json'},
        physical_lunar_mapping_certified=False,physical_accuracy_claimed=False,future_ephemerides_called=False,
        runtime_changed=False,passed=not failed,failed_criteria=failed)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(metrics=metrics,confirmations=confirmations,passed=report['passed'],failed=failed),indent=2),flush=True)
    return report['passed']


if __name__=='__main__':
    sys.exit(0 if audit() else 1)
