"""Frozen, bounded dynamic-step contrast of ordinary Solar DOP853; no runtime edits."""
import argparse
from dataclasses import replace
from decimal import Decimal as D,localcontext
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from time import perf_counter,process_time
import traceback
from unittest.mock import patch

import numpy as np
import scipy

from scripts.check_runtime_reliability376 import ROOT,PROTOCOL as P376,read,sha,write,seed_from,metrics,norm
from scripts.assess_kepler_phase import fingerprints,decimal_relative
from scripts.assess_sandbox_planets import states
from scripts.dynamic_step379 import observed_solver
from scripts.kepler_reference import propagate
from solar_simulator import accuracy
from solar_simulator.experiment import advance
from solar_simulator.recipe import runtime_fingerprint,_native
from solar_simulator.simulation import G

PLAN=ROOT/'scripts/runtime-step-379-plan.json'
OLD_REPORT=ROOT/'docs/runtime-reliability-376-validation.json'
OLD_ARRAYS=ROOT/'scripts/validation/runtime-reliability-376.npz'


def prepare():
    old=read(P376);proof=read(OLD_REPORT)
    if sha(P376)!=proof['protocol_SHA256'] or sha(OLD_ARRAYS)!=proof['arrays_SHA256']:raise ValueError('Changed376 evidence')
    cases=[c for c in old['cases'] if c['id'].startswith('high99')]
    jobs=[j for j in old['jobs'] if j['case'].startswith('high99') and j['profile']=='strict'
          and j['coordinates']=='relative' and j['schedule']=='grid']
    assert len(cases)==2 and len(jobs)==4 and all(len(c['epochs'])==49 for c in cases)
    source=fingerprints()
    for name in ('scripts/dynamic_step379.py','scripts/check_runtime_step379.py','scripts/assess_runtime_step379.py',
        'scripts/check_runtime_reliability376.py','scripts/assess_runtime_reliability376.py',
        'scripts/assess_kepler_holdout.py','scripts/assess_sandbox_planets.py','docs/runtime-step-379-protocol.md'):
        source[name]=sha(ROOT/name)
    native=_native('rust')
    if '0cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601' not in native['files'].values():
        raise ValueError('Native changed from376')
    plan=dict(stage=379,schema=1,base_commit='941eda322366d5c8f2b53a05fc255da612fb0af9',
        cases=cases,jobs=jobs,G_hex=G.hex(),settings=old['settings'],coordinates='relative A/B, same COM/drift/tilted SI axes as376',
        divisor=32,variants=['disabled','dynamic32'],
        input_SHA256={str(p.relative_to(ROOT)):sha(p) for p in (P376,OLD_REPORT,OLD_ARRAYS)},source_SHA256=source,
        environment=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,native=native,
            fingerprint=runtime_fingerprint('rust')),
        peri_indices={c['id']:[i for i,t in enumerate(c['epochs']) if
            (min(t/c['period_nominal_seconds'],abs(t/c['period_nominal_seconds']-1))<=.01 if c['id'].endswith('peri')
             else abs(t/c['period_nominal_seconds']-.5)<=.01)] for c in cases},
        budget=dict(CPU_seconds=120,wall_seconds=300,private_bytes=1024**3,artifact_bytes=64*1024**2,
            guard_stop_CPU=110,guard_stop_wall=280,guard_stop_private=900*1024**2,guard_stop_disk=56*1024**2),
        allocation_CPU=dict(primary=65,independent_audit=25,supervision=10,reserve=20),
        estimate='376 took29.45worker CPU for36jobs+8suffixes+4refs. Here8jobs+2refs, d32 prior RHS~1.12x; estimate15..60CPU total, <250MiB private, <8MiB outputs. Not a measured new benchmark.',
        reference='Exact binary64 IC/G/masses, Decimal f/g70/100 matched376; independent mpmath orbital-basis80/110 all98epochs',
        necessary_further_study='All4 cases: both sampled max r/v <=0.9 baseline; no peri/endpoint r/v worsening above1e-6m/1e-12m/s reference checks; RHS <=2x. Necessary only, never production GO.',
        scope='49 packet endpoints, not continuous maxima or JPL/physical accuracy. No parameter search, no carry/sumprod, no production changes.')
    write(PLAN,plan);print('Frozen plan',sha(PLAN),flush=True)


def verify_plan():
    p=read(PLAN)
    for name,digest in (p['source_SHA256']|p['input_SHA256']).items():
        if sha(ROOT/name)!=digest:raise ValueError('Frozen input/source changed: '+name)
    if G.hex()!=p['G_hex']:raise ValueError('Changed G')
    if runtime_fingerprint('rust')!=p['environment']['fingerprint']:raise ValueError('Changed scientific environment')
    return p


def run(output):
    p=verify_plan();plan_sha=sha(PLAN);output.mkdir(parents=True,exist_ok=False)
    cpu0=process_time();wall0=perf_counter();references={};rows=[];failure=None
    def budget():
        if process_time()-cpu0>95 or perf_counter()-wall0>250:raise TimeoutError('Early cooperative379 stop; external aggregate guard remains110CPU/280wall')
    try:
        old=read(OLD_REPORT)
        with localcontext() as ctx:
            ctx.prec=130
            for case in p['cases']:
                relative=decimal_relative(np.array(case['initial']));mu=D.from_float(G)*sum(map(D.from_float,case['masses']))
                expected=[];r_gap=v_gap=D(0)
                for t in case['epochs']:
                    low=propagate(relative[:3],relative[3:],mu,D.from_float(t),precision=70)
                    high=propagate(relative[:3],relative[3:],mu,D.from_float(t),precision=100)
                    r_gap=max(r_gap,norm([a-b for a,b in zip(low[0],high[0])]))
                    v_gap=max(v_gap,norm([a-b for a,b in zip(low[1],high[1])]))
                    expected.append(high);budget()
                historical=[tuple(tuple(map(D,g)) for g in row) for row in old['references'][case['id']]['values']]
                if expected!=historical or expected[0]!=(relative[:3],relative[3:]) or r_gap>=D('1e-6') or v_gap>=D('1e-12'):
                    raise ArithmeticError('Reference changed or unresolved')
                references[case['id']]=expected
                write(output/(case['id']+'-reference.json'),dict(values=[[list(map(str,g)) for g in row] for row in expected],
                    maximum_precision_r=str(r_gap),maximum_precision_v=str(v_gap),exact376=True))
        for variant in p['variants']:  # ALL four disabled controls must pass before any cap.
            for job in p['jobs']:
                case=next(c for c in p['cases'] if c['id']==job['case']);mu=G*sum(case['masses'])
                name=job['id']+'__'+variant;current=seed_from(case,job);values=[states(current.bodies)]
                step_rows=[];trial_rows=[];packets=[];error=None
                start=perf_counter();cpu=process_time();original=accuracy.PerBodyDOP853;original_ivp=accuracy.solve_ivp
                try:
                    with (output/(name+'-states.jsonl')).open('x',encoding='utf8') as journal:
                        journal.write(json.dumps(dict(time=current.time,state=values[0].tolist()))+'\n');journal.flush()
                        for i,t in enumerate(case['epochs'][1:],1):
                            method=observed_solver(mu,None if variant=='disabled' else p['divisor'],i,step_rows,trial_rows,budget)
                            def solve(*args,**kwargs):
                                result=original_ivp(*args,**kwargs);packets.append(dict(packet=i,nfev=result.nfev,success=result.success));return result
                            with patch.object(accuracy,'PerBodyDOP853',method),patch.object(accuracy,'solve_ivp',solve):
                                current=advance(replace(current,settings=replace(current.settings,dt=t-current.time)),1)
                            if current.time!=t:raise ArithmeticError('Packet schedule changed')
                            values.append(states(current.bodies));journal.write(json.dumps(dict(time=t,state=values[-1].tolist()))+'\n');journal.flush();budget()
                except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
                finally:
                    if accuracy.PerBodyDOP853 is not original or accuracy.solve_ivp is not original_ivp:raise RuntimeError('Patch leaked')
                    integration_cpu=process_time()-cpu;integration_wall=perf_counter()-start
                    np.savez_compressed(output/(name+'.npz'),states=np.array(values),epochs=np.array(case['epochs'][:len(values)]),
                        steps=np.array(step_rows).reshape(-1,13),trials=np.array(trial_rows).reshape(-1,4))
                    detail=dict(job=job,variant=variant,complete=error is None,error=error,
                        integration_CPU_seconds=integration_cpu,integration_wall_seconds=integration_wall,packets=packets,
                        RHS=sum(v['nfev'] for v in packets),accepted_steps=len(step_rows),rejected_trials=sum(v[11] for v in step_rows),
                        array_SHA256=sha(output/(name+'.npz')))
                    if error is None:
                        if variant=='disabled':
                            with np.load(OLD_ARRAYS,allow_pickle=False) as old_data:
                                exact=np.array_equal(np.array(values).view(np.uint64),old_data[job['id']+'__states'].view(np.uint64))
                            if not exact:raise ArithmeticError('Disabled observer changed376 baseline')
                            detail['baseline376_bit_exact']=True
                        maximum,per_epoch=metrics(values,references[case['id']],case['masses'])
                        detail.update(maxima=maximum,per_epoch=per_epoch,
                            maximum_indices={k:int(np.argmax([r[k] for r in per_epoch])) for k in ('r','v','E','L','P')},
                            pericentre={k:max(per_epoch[i][k] for i in p['peri_indices'][case['id']]) for k in ('r','v')},
                            endpoint={k:per_epoch[-1][k] for k in ('r','v')})
                    write(output/(name+'.json'),detail);rows.append(detail);print(name,detail.get('maxima'),flush=True)
                if error:raise RuntimeError(error['message'])
                budget()
    except BaseException as exc:failure=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    finally:
        verify_plan()
        write(output/'receipt.json',dict(complete=failure is None and len(rows)==8,failure=failure,plan_SHA256=plan_sha,
            jobs=rows,CPU_seconds=process_time()-cpu0,wall_seconds=perf_counter()-wall0,
            files={v.name:sha(v) for v in output.iterdir() if v.is_file()}))
    if failure:raise RuntimeError(failure['message'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('prepare','run'));parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.mode=='prepare':prepare()
    elif args.output is None:parser.error('--output required')
    else:run(args.output)
