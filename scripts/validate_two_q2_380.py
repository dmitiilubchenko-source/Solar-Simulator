"""Fixed short two-figure qualification; model evidence, not annual/JPL approval."""
import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
from time import process_time,perf_counter
import traceback

import numpy as np
from scipy.spatial.transform import Rotation

from scripts.assess_kepler_phase import ROOT,fingerprints
from scripts.check_runtime_reliability376 import sha,read,write
from scripts.two_q2_fixture380 import fixture
from scripts.two_q2_reference380 import reference,independent_invariants
from solar_simulator.experiment import create_experiment,advance
from solar_simulator.nbody_rotation import invariants
from solar_simulator.recipe import runtime_fingerprint
from solar_simulator.storage import to_document,from_document

PLAN=ROOT/'scripts/two-q2-380-plan.json'


def prepare(template=None):
    cases=[]
    for third in (False,True):
        b,r,s=fixture(third);state=create_experiment(b,s,rotations=r)
        cases.append(dict(id='three-bodies' if third else 'two-bodies',initial=to_document(state),epochs=np.linspace(0.,4000.,65).tolist()))
    sources=fingerprints()
    for name in ('scripts/two_q2_fixture380.py','scripts/two_q2_reference380.py','scripts/validate_two_q2_380.py'):
        sources[name]=sha(ROOT/name)
    levels=[dict(id='coarse',rtol=1e-9,position_atol=1e-6,velocity_atol=1e-10,spin_factor=100.),
        dict(id='standard',rtol=1e-11,position_atol=1e-8,velocity_atol=1e-12,spin_factor=1.),
        dict(id='fine',rtol=3e-13,position_atol=3e-10,velocity_atol=3e-14,spin_factor=.03)]
    plan=dict(stage=380,schema=1,base_commit='576a2fa0fbe77580da532659cd0843b5f03b2f6d',cases=cases,
        levels=levels,backends=['python','rust'],reference_rtol=[3e-11,3e-13],source_SHA256=sources,
        environment=runtime_fingerprint('rust'),units='SI; inertial positions/velocities/S, body-to-inertial unit quaternion',
        model='Newton monopoles plus total-degree-two M-Q per figure; no Q-Q/tides/EIH/contacts',
        criteria=dict(energy_drift=1e-8,angular_drift=1e-8,linear_drift=1e-12,quaternion_norm=1e-8,
            reference_difference=1e-7,reference_uncertainty=1e-8,empirical_tolerance_convergence='standard closer than coarse to fine',
            gradients='independent potential position/attitude gradients relative2e-6, reaction1e-13, angular balance2e-12',
            old_scenarios='8cases/24canonical snapshots byte-identical; same-packet save/resume exact'),
        budget=dict(CPU_seconds=120,wall_seconds=300,private_bytes=1024**3,artifact_bytes=64*1024**2),
        estimate='12 short cold DOP trajectories4000s/65epochs plus4 independent RK45; estimate10..60CPU, <256MiB worker private, <8MiB results',
        scope='Synthetic rigid model only; not real Earth/Moon accuracy or replacement of source-bound qualification375')
    if template is not None:
        original=read(template)
        for key in ('cases','levels','backends','reference_rtol','criteria','units','model'):
            if plan[key]!=original[key]:raise ValueError('Continuation changed original scientific inputs')
        plan['continuation']=dict(original_plan=str(template.relative_to(ROOT)),original_plan_SHA256=sha(template),
            result='docs/two-q2-380-initial.json',arrays='scripts/validation/two-q2-380-initial.npz',
            result_SHA256=sha(ROOT/'docs/two-q2-380-initial.json'),arrays_SHA256=sha(ROOT/'scripts/validation/two-q2-380-initial.npz'),
            reason='Original stopped after first convergence comparison at binary64 floor. Reuse all completed arrays, collect all original FAIL, add single-invocation convergence with identical physics/levels/epochs.',
            supplement='Python backend only, both systems, same three tolerance levels; one integrate call per trajectory rather than64 cold packets. Same standard-fine < coarse-fine criterion.')
        plan['budget']=dict(CPU_seconds=105,wall_seconds=280,private_bytes=1024**3,artifact_bytes=54*1024**2)
        plan['estimate']='9 remaining cold DOP jobs +2 fresh RK45 +6 continuous DOP jobs; estimate10..60CPU,<256MiB,<8MiB. Prior10.953125CPU/9.06wall retained; aggregate120CPU/300wall/64MiB.'
    write(PLAN,plan);print('Frozen two-Q2 plan',sha(PLAN))


def verify(plan_path=None, expected_sha=None):
    plan_path=Path(plan_path) if plan_path is not None else PLAN
    if plan_path.resolve()!=PLAN.resolve() and expected_sha is None:raise ValueError('Explicit plan SHA256 required')
    if expected_sha is not None and sha(plan_path)!=expected_sha:raise ValueError('Plan SHA256 mismatch')
    p=read(plan_path)
    if plan_path.resolve()!=PLAN.resolve():
        original=read(PLAN)
        for key in ('cases','levels','backends','reference_rtol','criteria','units','model'):
            if p[key]!=original[key]:raise ValueError('Changed scientific contract380: '+key)
        required={name for name in original['source_SHA256'] if not name.startswith('.venv/')}
        if not required<=set(p['source_SHA256']):
            raise ValueError('Missing frozen sources380')
    for name,digest in p['source_SHA256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Frozen source changed:'+name)
    if runtime_fingerprint('rust')!=p['environment']:raise ValueError('Scientific environment changed')
    return p


def represented(states):
    return dict(positions=np.array([[[b.position.x,b.position.y,b.position.z] for b in s.bodies] for s in states]),
        velocities=np.array([[[b.velocity.x,b.velocity.y,b.velocity.z] for b in s.bodies] for s in states]),
        orientation=np.array([[Rotation.from_quat(np.roll(r.quaternion,-1)).as_matrix() for r in s.rotations] for s in states]),
        spins=np.array([[r.angular_momentum for r in s.rotations] for s in states]),
        quaternions=np.array([[r.quaternion for r in s.rotations] for s in states]))


def difference(a,b,document):
    p=np.array([v['position'] for v in document['bodies']]);v=np.array([x['velocity'] for x in document['bodies']])
    position=max(np.linalg.norm(p[i]-p[j]) for i in range(len(p)) for j in range(i))
    velocity=max(np.linalg.norm(v[i]-v[j]) for i in range(len(v)) for j in range(i))
    spin=np.array([np.linalg.norm(r['angular_momentum']) for r in document['rotations']])
    return dict(position=float(np.max(np.linalg.norm(a['positions']-b['positions'],axis=2))/position),
        velocity=float(np.max(np.linalg.norm(a['velocities']-b['velocities'],axis=2))/velocity),
        orientation=float(np.max(np.linalg.norm(a['orientation']-b['orientation'],axis=(2,3)))),
        spin=float(np.max(np.linalg.norm(a['spins']-b['spins'],axis=2)/spin)))


def run(output, *, plan_path=None, expected_sha=None):
    plan_path=Path(plan_path) if plan_path is not None else PLAN
    p=verify(plan_path,expected_sha);output.mkdir(parents=True,exist_ok=False);cpu0=process_time();wall0=perf_counter();rows=[];arrays={};failure=None;comparisons=[];continuous=[]
    prior=[]
    if 'continuation' in p:
        continuation=p['continuation']
        for key in ('original_plan','result','arrays'):
            if sha(ROOT/continuation[key])!=continuation[key+'_SHA256']:raise ValueError('Changed continuation input:'+key)
        old=read(ROOT/continuation['result']);prior=old['rows']
        with np.load(ROOT/continuation['arrays'],allow_pickle=False) as data:arrays={key:data[key] for key in data.files}
        if len(prior)!=3 or old['complete'] or old['failure']['message']!='Tolerance convergence not established':
            raise ValueError('Unexpected first attempt; do not silently reuse')
    def budget():
        if process_time()-cpu0>95 or perf_counter()-wall0>250:raise TimeoutError('Early two-Q2 qualification stop')
    try:
        for case in p['cases']:
            doc=case['initial'];times=case['epochs'];reference_rows=[]
            for k,tolerance in enumerate(p['reference_rtol']):
                prefix=case['id']+'__reference'+str(k)+'__'
                if prefix+'positions' in arrays:
                    reference_rows.append({key.removeprefix(prefix):value for key,value in arrays.items() if key.startswith(prefix)})
                    continue
                before=process_time();ref=reference(doc,times,tolerance);budget()
                for key,value in ref.items():
                    if key!='RHS':arrays[case['id']+'__reference'+str(k)+'__'+key]=value
                reference_rows.append(ref)
                write(output/(case['id']+'-reference'+str(k)+'.json'),dict(CPU_seconds=process_time()-before,RHS=ref['RHS']))
            gap=difference(*reference_rows,doc)
            if max(gap.values())>=p['criteria']['reference_uncertainty']:raise ArithmeticError('Independent reference unresolved')
            for backend in p['backends']:
                solutions=[]
                for level in p['levels']:
                    name=case['id']+'__'+backend+'__'+level['id']
                    if name+'__positions' in arrays:
                        solutions.append({key.removeprefix(name+'__'):value for key,value in arrays.items() if key.startswith(name+'__')})
                        row=next(r for r in prior if (r['case'],r['backend'],r['level'])==(case['id'],backend,level['id']))
                        rows.append(row);continue
                    initial=from_document(doc)
                    tune=lambda values:tuple(replace(s,quaternion_atol=s.quaternion_atol*level['spin_factor'],momentum_atol=s.momentum_atol*level['spin_factor']) for s in values)
                    current=replace(initial,settings=replace(initial.settings,backend=backend,rtol=level['rtol'],
                        position_atol=level['position_atol'],velocity_atol=level['velocity_atol']),
                        rotations=tune(initial.rotations),initial_rotations=tune(initial.initial_rotations))
                    states=[current];started=perf_counter();cpu=process_time();name=case['id']+'__'+backend+'__'+level['id']
                    with (output/(name+'.jsonl')).open('x',encoding='utf8') as journal:
                        for target in times[1:]:
                            current=advance(replace(current,settings=replace(current.settings,dt=target-current.time)),1)
                            if current.time!=target:raise ArithmeticError('Packet time changed')
                            states.append(current);journal.write(json.dumps(dict(time=current.time,document=to_document(current)))+'\n');journal.flush();budget()
                    values=represented(states);solutions.append(values)
                    for key,value in values.items():arrays[name+'__'+key]=value
                    inv=[];independent=[]
                    masses=np.array([b['mass'] for b in doc['bodies']]);I=[np.array(r['figure']['moments']) for r in doc['rotations']]
                    for index,state in enumerate(states):
                        E,P,L=invariants(state.bodies,state.rotations);inv.append((E,[P.x,P.y,P.z],[L.x,L.y,L.z]))
                        independent.append(independent_invariants(values['positions'][index],values['velocities'][index],values['orientation'][index],values['spins'][index],masses,I))
                    energy=np.array([v[0] for v in inv]);mom=np.array([v[1] for v in inv]);angular=np.array([v[2] for v in inv])
                    otherE=np.array([v[0] for v in independent]);otherP=np.array([v[1] for v in independent]);otherL=np.array([v[2] for v in independent])
                    if not np.allclose(energy,otherE,rtol=1e-12) or not np.allclose(angular,otherL,rtol=1e-12) or not np.allclose(mom,otherP,rtol=1e-12):
                        raise ArithmeticError('Independent invariant values disagree')
                    row=dict(case=case['id'],backend=backend,level=level['id'],CPU_seconds=process_time()-cpu,wall_seconds=perf_counter()-started,
                        energy_drift=float(max(abs(energy-energy[0]))/abs(energy[0])),angular_drift=float(max(np.linalg.norm(angular-angular[0],axis=1))/np.linalg.norm(angular[0])),
                        linear_drift=float(max(np.linalg.norm(mom-mom[0],axis=1))/(sum(masses)*max(np.linalg.norm(values['velocities'][0],axis=1)))),
                        quaternion_norm=float(np.max(np.abs(np.linalg.norm(values['quaternions'],axis=2)-1))),
                        reference_difference=difference(values,reference_rows[1],doc),reference_uncertainty=gap)
                    write(output/(name+'.json'),row);rows.append(row);print(name,row,flush=True)
                convergence=dict(case=case['id'],backend=backend,coarse_fine=difference(solutions[0],solutions[2],doc),standard_fine=difference(solutions[1],solutions[2],doc))
                write(output/(case['id']+'__'+backend+'-convergence.json'),convergence)
                comparisons.append(convergence)
            if 'continuation' in p or p.get('continuous_control',False):
                from solar_simulator.nbody_rotation import integrate
                values=[]
                for level in p['levels']:
                    initial=from_document(doc)
                    spin=tuple(replace(s,quaternion_atol=s.quaternion_atol*level['spin_factor'],momentum_atol=s.momentum_atol*level['spin_factor']) for s in initial.rotations)
                    samples=integrate(initial.bodies,spin,times,rtol=level['rtol'],position_atol=level['position_atol'],velocity_atol=level['velocity_atol'],relative_pair=('A','B'))
                    states=[replace(initial,bodies=tuple(b),rotations=r,time=t) for t,(b,r) in zip(times,samples)]
                    data=represented(states);values.append(data)
                    for key,value in data.items():arrays[case['id']+'__continuous__'+level['id']+'__'+key]=value
                    budget()
                row=dict(case=case['id'],backend='python',coarse_fine=difference(values[0],values[2],doc),standard_fine=difference(values[1],values[2],doc),
                    reference_differences=[difference(v,reference_rows[1],doc) for v in values])
                continuous.append(row);write(output/(case['id']+'__continuous-convergence.json'),row)
        failed=[dict(case=r['case'],backend=r['backend'],level=r['level'],criterion=k) for r in rows for k in ('energy_drift','angular_drift','linear_drift','quaternion_norm') if r[k]>=p['criteria'][k]]
        failed += [dict(case=r['case'],backend=r['backend'],level=r['level'],criterion='fine_reference') for r in rows if r['level']=='fine' and max(r['reference_difference'].values())>=p['criteria']['reference_difference']]
        failed += [dict(case=r['case'],backend=r['backend'],criterion='packet_tolerance_convergence') for r in comparisons if max(r['standard_fine'].values())>=max(r['coarse_fine'].values())]
        failed += [dict(case=r['case'],backend='python',criterion='continuous_tolerance_convergence') for r in continuous if max(r['standard_fine'].values())>=max(r['coarse_fine'].values())]
    except BaseException as exc:failure=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    finally:
        verify(plan_path,expected_sha);np.savez_compressed(output/'states.npz',**arrays)
        write(output/'result.json',dict(stage=380,complete=failure is None and len(rows)==12,failure=failure,rows=rows,
            failed_criteria=failed if failure is None else None,packet_convergence=comparisons,continuous_convergence=continuous,
            plan_SHA256=sha(plan_path),arrays_SHA256=sha(output/'states.npz'),CPU_seconds=process_time()-cpu0,wall_seconds=perf_counter()-wall0,
            files={f.name:sha(f) for f in output.iterdir() if f.is_file()},current_runtime_qualified=False))
    if failure:raise RuntimeError(failure['message'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('prepare','run'));parser.add_argument('--output',type=Path)
    parser.add_argument('--plan',type=Path,default=PLAN);parser.add_argument('--continue-from',type=Path)
    parser.add_argument('--plan-sha256')
    args=parser.parse_args()
    if args.mode=='prepare':
        PLAN=args.plan.resolve()
        prepare(args.continue_from.resolve() if args.continue_from else None)
    elif args.output is None:parser.error('--output required')
    else:run(args.output,plan_path=args.plan,expected_sha=args.plan_sha256)
