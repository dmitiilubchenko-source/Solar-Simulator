"""Independent ten-body canonical research audit, explicit conditional scope."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.canonical_checkpoint import canonical_text, load, save, evolve
from scripts.canonical_initial import SIUnits
from scripts.independent_rigid_pn import matrix_rhs
from scripts.assess_rigid_pn import attitudes, convert_reference
from scripts.rigid_pn_model import invariants


def initial_checkpoint(policy):
    """Reuse checked p/S/units/basis bitwise; replace declared solver controls."""
    path=ROOT/policy['input_checkpoint']
    sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    if sha(policy['input_checkpoint'])!=policy['input_checkpoint_sha256']:
        raise ValueError('Changed immutable conditional ten-body checkpoint')
    cp=load(path);count=len(cp.parameters.orbital.masses)
    data=json.loads((ROOT/'src/solar_simulator/data/solar-system-moon-20261008.json').read_text(encoding='utf-8'))
    names=[b['name'] for b in data['bodies']]
    if (count!=10 or names!=policy['body_names'] or names[cp.parameters.index]!='Moon'
            or policy['physical_lunar_mapping_certified'] is not False):
        raise ValueError('Incompatible conditional ten-body contract')
    meta=cp.metadata;units=SIUnits(**{k:v for k,v in meta['units'].items() if k!='kind'})
    s=np.array(cp.state[:-4]).reshape(3,count,3)[2];spin=np.linalg.norm(s[cp.parameters.index])
    spin_atol=np.full((count,3),policy['zero_point_spin_atol_model_units'])
    spin_atol[cp.parameters.index]=policy['figure_spin_atol_relative_to_initial_norm']*spin
    atol=np.r_[np.full(3*count,policy['position_atol_m']/units.length_m),
        np.repeat(np.array(cp.parameters.orbital.masses)*policy['momentum_atol_equivalent_velocity_m_s']/units.velocity_m_s,3),
        spin_atol.ravel(),np.full(4,policy['quaternion_atol'])]
    meta['integration']=dict(method='canonical-per-block-DOP853',rtol=policy['production_rtol'],atol=atol.tolist(),
                             max_step=policy['max_step_seconds']/units.time_s)
    extras=[policy['input_checkpoint'],'scripts/assess_canonical_solar.py',
            'scripts/canonical-solar-policy.json','tests/test_canonical_solar.py']
    recorded={r['path'] for r in meta['provenance']['sources']}
    meta['provenance']['sources'] += [dict(path=p,sha256=sha(p)) for p in extras if p not in recorded]
    cp=replace(cp,metadata_json=canonical_text(meta))
    return cp,units,names


def differences(first, first_r, second, second_r, units, count, earth, figure, spin_scale):
    a,b=np.asarray(first),np.asarray(second);ra,rb=np.asarray(first_r),np.asarray(second_r)
    if (type(count) is not int or count<2 or a.shape!=b.shape or a.ndim!=2 or a.shape[1]!=9*count
            or ra.shape!=rb.shape or ra.shape!=(len(a),3,3)
            or not all(np.all(np.isfinite(v)) for v in [a,b,ra,rb])
            or not 0<=earth<count or not 0<=figure<count or earth==figure
            or not np.isfinite(spin_scale) or spin_scale<=0):
        raise ValueError('Matched finite canonical/orientation grids and scales required')
    aa,bb=a.reshape(-1,3,count,3),b.reshape(-1,3,count,3)
    positions=np.linalg.norm((aa[:,0]-bb[:,0])*units.length_m,axis=-1)
    internal=((aa[:,0,figure]-aa[:,0,earth])-(bb[:,0,figure]-bb[:,0,earth]))*units.length_m
    return dict(positions_m=float(positions.max()),positions_per_body_m=positions.max(axis=0).tolist(),
        earth_moon_position_m=float(np.linalg.norm(internal,axis=1).max()),
        figure_spin_relative=float(np.linalg.norm(aa[:,2,figure]-bb[:,2,figure],axis=1).max()/spin_scale),
        attitude_matrix=float(np.linalg.norm(ra-rb,axis=(1,2)).max()))


def audit():
    output=ROOT/'docs/canonical-solar-validation.json'
    if output.exists():raise FileExistsError('Preserve ten-body canonical audit')
    policy=json.loads((ROOT/'scripts/canonical-solar-policy.json').read_text(encoding='utf-8'))
    cp,units,names=initial_checkpoint(policy);params=cp.parameters;count=len(names);figure=params.index;earth=names.index('Earth')
    sources={r['path']:r['sha256'] for r in cp.metadata['provenance']['sources']}
    sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    work=ROOT/'.tools/rotation61';work.mkdir(exist_ok=True)
    times=np.linspace(0.,policy['duration_seconds']/units.time_s,policy['samples'])
    initial=np.array(cp.state);spin_scale=np.linalg.norm(initial[:-4].reshape(3,count,3)[2,figure]);jobs={};arrays={}
    def keep(name,states):
        path=work/(name+'.npz')
        with path.open('xb') as stream:np.savez_compressed(stream,times=times,states=states)
        arrays[path.relative_to(ROOT).as_posix()]=sha(path.relative_to(ROOT))
    def production(name,start,grid):
        print(name,'started',flush=True);timer=time.perf_counter();end,states=evolve(start,grid,source_root=ROOT)
        jobs[name]=time.perf_counter()-timer;print(name,round(jobs[name],2),'seconds',flush=True)
        return end,states
    save(work/'initial.json',cp);end,primary=production('production',cp,times);keep('production',primary)
    strict_meta=cp.metadata;strict_meta['integration'].update(rtol=policy['tighter_rtol'],
        atol=(np.array(strict_meta['integration']['atol'])*policy['tighter_atol_factor']).tolist(),
        max_step=policy['tighter_max_step_seconds']/units.time_s)
    _,strict=production('tighter',replace(cp,metadata_json=canonical_text(strict_meta)),times);keep('tighter',strict)
    r=Rotation.from_quat(np.roll(initial[-4:],-1)).as_matrix();matrix_start=np.r_[initial[:-4],r.ravel()]
    spin_slice=slice(6*count+3*figure,6*count+3*figure+3)
    matrix_start[spin_slice]=r.T@initial[spin_slice]
    scales=np.linalg.norm(initial[:-4].reshape(3,count,3),axis=-1);point=[i for i in range(count) if i!=figure]
    raw_refs=[];references=[]
    for i,rtol in enumerate(policy['reference_rtols']):
        atol=rtol*policy['reference_atol_over_rtol']*np.r_[np.repeat(scales.ravel(),3),np.ones(9)]
        for index in point:atol[6*count+3*index:6*count+3*index+3]=policy['zero_point_spin_atol_model_units']
        name=f'reference-{i}';print(name,'started',flush=True);timer=time.perf_counter()
        result=solve_ivp(lambda t,y:matrix_rhs(t,y,params.orbital.masses,params.orbital.c,params.figure.moments,figure),
            (0.,float(times[-1])),matrix_start,t_eval=times,method='RK45',rtol=rtol,atol=atol,
            max_step=policy['max_step_seconds']/units.time_s)
        if (not result.success or result.y.shape!=(9*count+9,len(times))
                or not np.array_equal(result.t,times) or not np.all(np.isfinite(result.y))):
            raise ValueError(f'Invalid independent integration: {name}')
        raw=result.y.T;jobs[name]=time.perf_counter()-timer;keep(name,raw)
        raw_refs.append(raw);references.append(convert_reference(raw,count,figure))
        print(name,round(jobs[name],2),'seconds',flush=True)
    split=policy['split_sample'];middle,first=production('restart-prefix',cp,times[:split+1])
    save(work/'middle.json',middle);loaded=load(work/'middle.json')
    final,last=production('restart-suffix',loaded,times[split:]);joined=np.vstack([first[:-1],last]);keep('restarted',joined)
    rotations=attitudes(primary)
    delta=lambda a,ra,b,rb:differences(a,ra,b,rb,units,count,earth,figure,spin_scale)
    checks=dict(reference=delta(primary[:,:-4],rotations,*references[-1]),
        reference_uncertainty=delta(*references[0],*references[1]),
        tighter=delta(primary[:,:-4],rotations,strict[:,:-4],attitudes(strict)),
        restart=delta(primary[:,:-4],rotations,joined[:,:-4],attitudes(joined)))
    values=[invariants(y,params) for y in primary];h=np.array([v[0] for v in values]);p=np.array([v[1] for v in values]);j=np.array([v[2] for v in values])
    if min(abs(h[0]),np.linalg.norm(j[0]),scales[1].sum())<=0:raise ValueError('Degenerate invariant scales')
    raw_r=np.concatenate([r[1] for r in references])
    metrics=dict(energy_relative=float(np.max(abs(h-h[0]))/abs(h[0])),
        momentum_scaled=float(np.linalg.norm(p-p[0],axis=1).max()/scales[1].sum()),
        angular_momentum_relative=float(np.linalg.norm(j-j[0],axis=1).max()/np.linalg.norm(j[0])),
        quaternion_norm=float(np.max(abs(np.linalg.norm(primary[:,-4:],axis=1)-1))),
        reference_rotation_orthogonality=float(np.linalg.norm(np.swapaxes(raw_r,1,2)@raw_r-np.eye(3),axis=(1,2)).max()),
        reference_rotation_determinant=float(np.max(abs(np.linalg.det(raw_r)-1))))
    for prefix,result in checks.items():
        for k in ['positions_m','earth_moon_position_m','figure_spin_relative','attitude_matrix']:metrics[prefix+'_'+k]=result[k]
    points_zero=all(np.array_equal(states[:,:9*count].reshape(-1,3,count,3)[:,2,point],np.zeros((len(states),len(point),3)))
                    for states in [primary,strict,joined]+raw_refs)
    original=load(ROOT/policy['input_checkpoint'])
    confirmations=dict(point_spins_exactly_zero=points_zero,
        checkpoint_bitwise=np.array_equal(np.array(middle.state).view(np.uint64),np.array(loaded.state).view(np.uint64)),
        initial_state_bitwise=np.array_equal(initial.view(np.uint64),np.array(original.state).view(np.uint64)),
        metadata_preserved=cp.metadata_json==end.metadata_json==loaded.metadata_json==final.metadata_json,
        source_hashes_preserved=sources=={p:sha(p) for p in sources})
    failed=[k for k,limit in policy['criteria'].items() if not metrics[k]<limit]+[k for k in policy['required_true'] if not confirmations[k]]
    report=dict(change=61,policy=policy,metrics=metrics,confirmations=confirmations,components=checks,job_seconds=jobs,
        sample_times_seconds=(times*units.time_s).tolist(),initial_state=initial.tolist(),units_SI=vars(units),
        code_and_input_sha256=sources,trajectory_archives=arrays,
        checkpoint_files={p.relative_to(ROOT).as_posix():sha(p.relative_to(ROOT)) for p in work.glob('*.json') if p.name!='before.json'},
        physical_lunar_mapping_certified=False,physical_accuracy_claimed=False,future_ephemerides_called=False,
        runtime_changed=False,passed=not failed,failed_criteria=failed)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(metrics=metrics,confirmations=confirmations,passed=report['passed'],failed=failed),indent=2),flush=True)
    return report['passed']


if __name__=='__main__':sys.exit(0 if audit() else 1)
