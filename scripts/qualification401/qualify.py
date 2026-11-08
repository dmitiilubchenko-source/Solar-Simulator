"""Finite source-bound continuation401. Never runs the two completed400 cases."""
import argparse
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from scripts import q2_execution398 as q
from scripts.q2_interface_recovery401 import authenticated_archive,canonical,physical_bits,sha,validate_legacy_point,logical_path,BASE,CANDIDATE
W=R/'.tools/qualification401-20261108'
PLAN=W/'plan.json'


def plan():return json.loads(PLAN.read_bytes())
def put(name,value):q.atomic_json(W/name,value)
def read(name):return json.loads((W/name).read_bytes())
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def lf_profile(fp):return sha((json.dumps(fp,indent=2)+'\n').encode())


def activate(role):
    p=plan();root=Path(p['source_roots'][role]);commit=p[role]
    if git(root,'rev-parse','HEAD')!=commit or git(root,'status','--porcelain'):raise ValueError('Wrong/dirty source role')
    sys.path.insert(0,str(root/'src'))
    names=('experiment','storage','cli','inspection','application_profiles','recipe','accuracy','nbody_rotation')
    m={n:importlib.import_module('solar_simulator.'+n) for n in names}
    import solar_simulator,numpy,scipy,solar_native
    from importlib.metadata import version
    from scripts.q2_source_adapter396 import require_origins
    prefix=Path(p['interpreter']).parents[1]
    require_origins(solar_simulator.__file__,[numpy.__file__,scipy.__file__,solar_native.__file__],root,sys.prefix,prefix)
    if any(not Path(x.__file__).resolve().is_relative_to(root/'src') for x in m.values()):raise ValueError('Mixed source modules')
    fp=m['recipe'].runtime_fingerprint('rust');old=json.loads((R/'.tools/qualification395/candidate-environment.json').read_bytes())
    if role=='base':
        if fp!=old:raise ValueError('Actual optimized environment mismatch')
    else:
        if {k:v for k,v in fp.items() if k!='package_files'}!={k:v for k,v in old.items() if k!='package_files'}:raise ValueError('Candidate numeric dependency/native environment changed')
        changed={n for n in fp['package_files'].keys()|old['package_files'].keys() if fp['package_files'].get(n)!=old['package_files'].get(n)}
        if changed!={'app.py','inspection.py','inspection_view.py'}:raise ValueError('Unexpected actual package delta')
    compiled=getattr(solar_native,'solar_native',solar_native)
    q.require_sha(compiled.__file__,'651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091')
    identity=dict(role=role,commit=commit,tree=git(root,'rev-parse','HEAD^{tree}'),source=str(root),actual_import=solar_simulator.__file__,interpreter=sys.executable,prefix=sys.prefix,
        dependency_origins={k:x.__file__ for k,x in [('numpy',numpy),('scipy',scipy),('solar_native',solar_native)]},compiled_native=compiled.__file__,native_SHA256=q.sha(compiled.__file__),
        environment_LF_SHA256=lf_profile(fp),source_package_map_SHA256=sha(canonical(fp['package_files'])),
        versions=dict(python=sys.version,numpy=numpy.__version__,scipy=scipy.__version__,native=version('solar-native'),application=version('solar-simulator')),
        profile_kind='source, not wheel/portable')
    return m,identity,fp


def seed(m,case,backend):
    f=m['application_profiles']
    state=f.scenario('sun-earth',backend=backend) if case=='point' else f.lunar_rotation(backend=backend) if case=='one' else f.two_q2_demo(backend=backend)
    return replace(state,settings=replace(state.settings,dt=2.))


def recovery():
    p=plan();manifest,members,binding=authenticated_archive(p['archive400']);m,identity,fp=activate('base')
    for name,raw in members.items():
        if name.startswith('qualification400/'):
            local=R/'.tools/qualification400-20261108'/name.removeprefix('qualification400/')
            if not local.is_file() or local.read_bytes()!=raw:raise ValueError('Local400 evidence differs from authenticated archive: '+name)
    core=json.loads(members['qualification400/report-core.json'])
    for row in core['short_source_comparison']['partial_files']:
        name='qualification400/'+logical_path(row['path'])
        if len(members[name])!=row['size'] or sha(members[name])!=row['sha256']:raise ValueError('Partial400 payload manifest mismatch')
    stop=json.loads(members['qualification400/final-source-check-resources.json'])
    if stop['record']['limit_reason']!='stage-CPU' or core['charged_CPU_seconds']!=96.3125:raise ValueError('Wrong historical resource status')
    rows={}
    for backend in ('python','rust'):
        payload_name='qualification400/final/base/point-'+backend+'.json';checkpoint_name='qualification400/final/base/point-'+backend+'-checkpoint.json'
        payload=json.loads(members[payload_name]);checkpoint=json.loads(members[checkpoint_name]);expected=m['storage'].to_document(seed(m,'point',backend))
        proof=validate_legacy_point(payload,checkpoint,expected)
        for doc in payload['documents']:
            if canonical(m['storage'].to_document(m['storage'].from_document(doc)))!=canonical(doc):raise ValueError('Historical state codec mismatch')
        if canonical(payload['legacy_initial'])!=canonical(m['cli'].report(m['storage'].from_document(expected))):raise ValueError('Historical initial diagnostics mismatch')
        rows['base__point__'+backend]=dict(**proof,archive_member=payload_name,payload_SHA256=sha(members[payload_name]),checkpoint_member=checkpoint_name,checkpoint_SHA256=sha(members[checkpoint_name]),source=identity,provenance=binding)
    put('base-environment.json',fp)
    put('recovery.json',dict(status='RECOVERED_TWO_AUTHENTICATED_CASES_NO_INTEGRATION',rows=rows,source=identity,archive_binding=binding,member_SHA256={n:sha(v) for n,v in members.items()},previous400_RESOURCE_STOP=stop,old400_results_not_modified=True))
    print('PASS recovery: exact archive/member/local SHA,2point IC/settings/raw/checkpoint/code provenance;0integrations',flush=True)


def delta():
    import ast
    from scripts.q2_presentation_delta400 import review,git as raw_git,APPROVED
    p=plan();base=Path(p['source_roots']['base']);candidate=Path(p['source_roots']['candidate'])
    result=review(base,candidate);m,identity,fp=activate('candidate')
    def tree(root,revision):
        rows={}
        for line in raw_git(root,'ls-tree','-r',revision).decode().splitlines():
            header,name=line.split('\t',1);mode,kind,oid=header.split();rows[name]=dict(mode=mode,kind=kind,Git_object_ID=oid)
        return rows
    a=tree(base,BASE);b=tree(candidate,CANDIDATE)
    if set(a)!=set(b) or {n for n in a if a[n]!=b[n]}!=set(APPROVED):raise ValueError('Full Git tree delta differs from3presentation paths')
    result['full_Git_tree_blob_identity']={n:dict(base=a[n],candidate=b[n]) for n in a}
    result['source']=identity;result['historical74_repeated']=False
    advance_tree=ast.parse((base/'src/solar_simulator/experiment.py').read_bytes())
    advance_function=next(n for n in advance_tree.body if isinstance(n,ast.FunctionDef) and n.name=='advance')
    point_calls=[n for n in ast.walk(advance_function) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='evolve_accurate']
    accuracy_tree=ast.parse((base/'src/solar_simulator/accuracy.py').read_bytes())
    accuracy_function=next(n for n in accuracy_tree.body if isinstance(n,ast.FunctionDef) and n.name=='evolve_accurate')
    solves=[n for n in ast.walk(accuracy_function) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='solve_ivp']
    if len(point_calls)!=1 or len(solves)!=1:raise ValueError('Historical point solver-call proof invalid')
    result['legacy_solver_call_proof']=dict(solver_invocations_per_completed_legacy_point_case=3,kind='Static control-flow proof, not historical instrumentation',
        chain='Authenticated helper400 has3completed advance(state,1) calls; validated positive2s point DOP settings; advance has1point evolve_accurate call and evolve_accurate1solve_ivp call; no inspection/storage integration.',
        historical_nfev=None,source_files_SHA256={n:q.sha(base/'src/solar_simulator'/n) for n in ('experiment.py','accuracy.py')})
    put('candidate-environment.json',fp);put('delta.json',result)
    print('PASS actual source AST/Git blob/inventory delta and actual candidate source fingerprint',identity['environment_LF_SHA256'],flush=True)


@contextmanager
def observed(m):
    import solar_native
    original_force=solar_native.point_acceleration;original=[(m[n],m[n].solve_ivp) for n in ('accuracy','nbody_rotation')]
    count=dict(solver_calls=0,RHS=0,nfev=0,native_calls=0,solves=[])
    def force(*a,**kw):count['native_calls']+=1;return original_force(*a,**kw)
    def wrap(solve):
        def call(fun,*a,**kw):
            count['solver_calls']+=1
            def rhs(*aa,**kk):count['RHS']+=1;return fun(*aa,**kk)
            result=solve(rhs,*a,**kw);count['nfev']+=int(result.nfev)
            count['solves'].append(dict(nfev=int(result.nfev),method=getattr(kw.get('method'),'__name__',str(kw.get('method'))),rtol=kw.get('rtol')))
            return result
        return call
    solar_native.point_acceleration=force
    for module,solve in original:module.solve_ivp=wrap(solve)
    try:yield count
    finally:
        solar_native.point_acceleration=original_force
        for module,solve in original:module.solve_ivp=solve


def run_cases(role):
    p=plan();m,identity,fp=activate(role)
    if fp!=read(role+'-environment.json'):raise ValueError('Environment changed after admission')
    source_path=Path(p['source_roots'][role]);tool=q.sha(Path(__file__))
    jobs=[x for x in p['new_jobs'] if x.startswith(role+'__')]
    for job in jobs:
        _,case,backend=job.split('__');directory=W/'jobs'/job;directory.mkdir(parents=True,exist_ok=False)
        state=seed(m,case,backend);doc=m['storage'].to_document(state)
        binding=dict(job=job,source=identity,plan_SHA256=q.sha(PLAN),tool_manifest_SHA256=q.sha(W/'tools-v3.json'),driver_SHA256=tool,adapter_SHA256=q.sha(R/'scripts/q2_interface_recovery401.py'),initial_SHA256=sha(canonical(doc)),epochs_seconds=[0.,2.,4.])
        q.atomic_json(directory/'started.json',q.envelope(binding))
        legacy=m['cli'].report(state);shown=m['inspection'].report(state)
        if canonical({k:v for k,v in shown.items() if k!='numerical_reliability'})!=canonical(legacy) or m['storage'].to_document(state)!=doc:raise ValueError('Inspection changed numerical state/diagnostics')
        if shown['numerical_reliability']['qualification']['current_trajectory_certified'] is not False:raise ValueError('Unexpected certification')
        states=[doc]
        with observed(m) as count:
            state=m['experiment'].advance(state,1);states.append(m['storage'].to_document(state))
            m['storage'].save(state,directory/'checkpoint.json');raw=(directory/'checkpoint.json').read_bytes();restored=m['storage'].load(directory/'checkpoint.json')
            m['inspection'].report(restored)
            if m['storage'].to_document(restored)!=states[-1] or (directory/'checkpoint.json').read_bytes()!=raw:raise ValueError('Read-only inspection/checkpoint changed')
            final=m['experiment'].advance(state,1);resumed=m['experiment'].advance(restored,1);states.append(m['storage'].to_document(final))
            if canonical(m['storage'].to_document(resumed))!=canonical(states[-1]):raise ValueError('Same-packet restart mismatch')
        if count['solver_calls']!=3 or count['RHS']!=count['nfev'] or count['native_calls']!=(count['RHS'] if backend=='rust' else 0):raise ValueError('Actual solver/native dispatch mismatch')
        payload=dict(case=case,backend=backend,epochs_seconds=[0.,2.,4.],documents=states,legacy_initial=legacy,native_calls=count['native_calls'],resume_exact=True)
        q.atomic_json(directory/'payload.json',payload);q.atomic_json(directory/'counters.json',count)
        files={n:dict(size=(directory/n).stat().st_size,sha256=q.sha(directory/n)) for n in ('started.json','checkpoint.json','payload.json','counters.json')}
        q.atomic_json(directory/'complete.json',q.envelope(dict(binding=binding,files=files,raw_binary64_SHA256=sha(physical_bits(states)))))
        print('COMPLETE',job,flush=True)
    after=m['recipe'].runtime_fingerprint('rust')
    if after!=fp or git(source_path,'status','--porcelain'):raise ValueError('Source/environment changed during cases')
    put(role+'-new-complete.json',dict(jobs=jobs,driver_SHA256=tool,environment_LF_SHA256=lf_profile(fp)))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['recovery','delta','base-runs','candidate-runs']);args=parser.parse_args()
    if args.phase=='recovery':recovery()
    elif args.phase=='delta':delta()
    else:run_cases('base' if args.phase=='base-runs' else 'candidate')


if __name__=='__main__':main()
