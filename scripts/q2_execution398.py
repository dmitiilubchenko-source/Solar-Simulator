"""Fixed Q2 qualification executor. No solver/force/evaluator replacement.

398 uses only explicitly labelled short probes. Full399 execution requires its
separately authorized sealed plan. Historical380/395/396 files stay read-only.
"""
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter,process_time
import traceback

from scripts.q2_source_adapter396 import sha,require_sha,require_environment,require_origins

ROOT=Path(__file__).resolve().parents[1]
CONTRACT='scripts/q2-qualification398-plan.json'
CONTRACT_SHA='b6131f0abeeec63ee2e324a34b22f6c96008e67e747fa94e9ee52b2795c0bd28'


def canonical(value):
    return json.dumps(value,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf8')


def atomic_json(path,value,*,fault=None):
    """Publish a fully fsynced new file with a no-replace hard link.

    Unsupported filesystems fail closed. An interrupted .partial stays partial.
    fault is a trusted test hook, never loaded or executed from JSON.
    """
    path=Path(path);temporary=path.with_name(path.name+'.partial')
    if path.exists():raise FileExistsError(path)
    with temporary.open('xb') as f:
        f.write(canonical(value)+b'\n');f.flush();os.fsync(f.fileno())
    if fault:fault('fsynced')
    os.link(temporary,path)
    temporary.unlink()


def envelope(value):
    return dict(payload=value,sha256=hashlib.sha256(canonical(value)).hexdigest())


def read_envelope(path):
    x=json.loads(Path(path).read_bytes())
    if type(x) is not dict or set(x)!= {'payload','sha256'} or hashlib.sha256(canonical(x['payload'])).hexdigest()!=x['sha256']:raise ValueError('Corrupt envelope')
    return x['payload']


def contract(root=ROOT):
    require_sha(Path(root)/CONTRACT,CONTRACT_SHA)
    p=json.loads((Path(root)/CONTRACT).read_bytes());jobs=p['jobs']
    ids=[x['id'] for x in jobs]
    if len(jobs)!=58 or len(set(ids))!=58 or any(Path(x).name!=x or '/' in x or '\\' in x for x in ids):raise ValueError('Wrong58-job contract')
    return p


def initialize(directory,execution):
    directory=Path(directory);directory.mkdir(exist_ok=False)
    atomic_json(directory/'run.json',envelope(execution))


def verify_complete(directory,binding):
    directory=Path(directory)
    if list(directory.glob('*.partial')):raise ValueError('Partial output is not a completed job')
    if not (directory/'complete.json').is_file():raise ValueError('Incomplete job; no controller continuation/re-execution authorized')
    row=read_envelope(directory/'complete.json')
    if row['binding']!=binding:raise ValueError('Mixed job/source/recipe/output binding')
    if set(row['files'])!={'initial.json','result.json','states.jsonl'}:raise ValueError('Incomplete job file manifest')
    for name,meta in row['files'].items():
        path=directory/name
        if not path.is_file() or path.stat().st_size!=meta['size']:raise ValueError('Missing/truncated job file')
        require_sha(path,meta['sha256'])
    result=json.loads((directory/'result.json').read_bytes())
    if read_envelope(directory/'initial.json')!=binding:raise ValueError('Corrupt initial binding')
    if result['binding']!=binding:raise ValueError('Mixed result owner')
    states=[]
    for line in (directory/'states.jsonl').read_bytes().splitlines():
        x=json.loads(line)
        if hashlib.sha256(canonical(x['payload'])).hexdigest()!=x['sha256']:raise ValueError('Corrupt state record')
        states.append(x['payload'])
    if len(states)!=row['frames'] or [x['time'] for x in states]!=result['epochs']:raise ValueError('Missing state epochs')
    result['documents']=[x['document'] for x in states]
    return result


def independent_by_id(p,v,R,S,document):
    """Adapt only source/body association of the unchanged380 scalar kernel.

    Put rotating sources first, in rotation order, so its positional source
    convention is true. Original A/B fixtures keep their exact reduction order.
    """
    import numpy as np
    from scripts.two_q2_reference380 import independent_invariants
    names=[x['name'] for x in document['bodies']];sources=[x['body'] for x in document['rotations']]
    if len(set(names))!=len(names) or len(set(sources))!=len(sources) or any(x not in names for x in sources):raise ValueError('Invalid observer body IDs')
    order=[names.index(x) for x in sources];order += [i for i in range(len(names)) if i not in order]
    masses=np.array([x['mass'] for x in document['bodies']]);inertias=[np.array(x['figure']['moments']) for x in document['rotations']]
    return independent_invariants(np.asarray(p)[order],np.asarray(v)[order],np.asarray(R),np.asarray(S),masses[order],inertias)


def require_arrays(values,document,epochs,*,runtime):
    import numpy as np
    T,N,K=len(epochs),len(document['bodies']),len(document['rotations'])
    shapes=dict(positions=(T,N,3),velocities=(T,N,3),orientation=(T,K,3,3),spins=(T,K,3))
    if runtime:shapes['quaternions']=(T,K,4)
    for key,shape in shapes.items():
        if key not in values:raise ValueError('Missing raw observable '+key)
        a=np.asarray(values[key])
        if a.shape!=shape or not np.isfinite(a).all():raise ValueError('Invalid raw observable '+key)
    if len(epochs)<2 or any(type(x) not in (int,float) for x in epochs) or not all(np.isfinite(epochs)) or not all(a<b for a,b in zip(epochs,epochs[1:])):raise ValueError('Invalid epochs')


def difference(a,b,document,epochs):
    from scripts.validate_two_q2_380 import difference as original
    import numpy as np
    require_arrays(a,document,epochs,runtime=False);require_arrays(b,document,epochs,runtime=False)
    p=np.array([x['position'] for x in document['bodies']]);v=np.array([x['velocity'] for x in document['bodies']])
    if max(np.linalg.norm(p[i]-p[j]) for i in range(len(p)) for j in range(i))<=0 or max(np.linalg.norm(v[i]-v[j]) for i in range(len(v)) for j in range(i))<=0 or any(np.linalg.norm(r['angular_momentum'])<=0 for r in document['rotations']):raise ValueError('Undefined historical normalization')
    return original({k:np.array(v) for k,v in a.items()},{k:np.array(v) for k,v in b.items()},document)


def drift(values,document,epochs,runtime_observables=None):
    """Exactly380 drift definitions, using its independent scalar Hamiltonian."""
    import numpy as np
    require_arrays(values,document,epochs,runtime=True)
    inv=[independent_by_id(values['positions'][i],values['velocities'][i],values['orientation'][i],values['spins'][i],document) for i in range(len(epochs))]
    E=np.array([x[0] for x in inv]);P=np.array([x[1] for x in inv]);L=np.array([x[2] for x in inv]);mass=sum(x['mass'] for x in document['bodies'])
    if runtime_observables is not None:
        supplied=[np.asarray(runtime_observables[k]) for k in ('E_J','P_kg_m_s','L_kg_m2_s')]
        for expected,actual in zip((E,P,L),supplied):
            if actual.shape!=expected.shape or not np.isfinite(actual).all() or not np.allclose(expected,actual,rtol=1e-12):raise ValueError('Independent/runtime observables disagree')
        E,P,L=supplied  # Original380 gates use runtime values, not a new reduction.
    v0=max(np.linalg.norm(x) for x in values['velocities'][0])
    if abs(E[0])==0 or np.linalg.norm(L[0])==0 or v0==0:raise ValueError('Undefined historical drift scale')
    return dict(energy_drift=float(max(abs(E-E[0]))/abs(E[0])),angular_drift=float(max(np.linalg.norm(L-L[0],axis=1))/np.linalg.norm(L[0])),linear_drift=float(max(np.linalg.norm(P-P[0],axis=1))/(mass*v0)),quaternion_norm=float(np.max(np.abs(np.linalg.norm(values['quaternions'],axis=2)-1))),observables=dict(E_J=E.tolist(),P_kg_m_s=P.tolist(),L_kg_m2_s=L.tolist()))


def source_equivalence(a,b):
    """Compare only matching recipes/backend/IC/epochs; no tolerance fallback."""
    import numpy as np
    for key in ('job','epochs','initial','settings'):
        if a[key]!=b[key]:raise ValueError('Incomparable source recipes '+key)
    require_arrays(a['arrays'],a['initial'],a['epochs'],runtime=True);require_arrays(b['arrays'],b['initial'],b['epochs'],runtime=True)
    validate_documents(a);validate_documents(b)
    exact=all(np.array(a['arrays'][k],dtype='float64').tobytes()==np.array(b['arrays'][k],dtype='float64').tobytes() for k in ('positions','velocities','quaternions','spins'))
    exact &= canonical(a['documents'])==canonical(b['documents']) and a['counters']==b['counters']
    from scripts.q2_frame_observer393 import orientation_angle
    angles=[[orientation_angle(x,y) for x,y in zip(qa,qb)] for qa,qb in zip(a['arrays']['quaternions'],b['arrays']['quaternions'])]
    return dict(exact=bool(exact),stable_SO3_angles_rad=angles,scope='Samebackend/recipe/IC/sourcepair only; not scientificaccuracy')


def validate_documents(result):
    """Check the raw saved states, not just matching ready-made result flags."""
    import numpy as np
    from scipy.spatial.transform import Rotation
    documents=result['documents'];epochs=result['epochs'];initial=result['initial'];values=result['arrays']
    initial_expected=initial_readout(initial) if result['job'].get('recipe')=='continuous' else None
    if len(documents)!=len(epochs):raise ValueError('Incomplete checkpoint history')
    for i,(doc,time) in enumerate(zip(documents,epochs)):
        if i==0 and initial_expected is not None and canonical(doc)!=canonical(initial):raise ValueError('Initial input checkpoint changed')
        if doc['time']!=time or len(doc['bodies'])!=len(initial['bodies']) or len(doc['rotations'])!=len(initial['rotations']):raise ValueError('Checkpoint epoch/layout mismatch')
        settings=dict(doc['settings']);expected=dict(initial['settings'])
        if result['job'].get('recipe')=='cold' and i:expected['dt']=time-epochs[i-1]
        if settings!=expected:raise ValueError('Checkpoint solver settings changed')
        for j,(body,original) in enumerate(zip(doc['bodies'],initial['bodies'])):
            if body['name']!=original['name'] or body['mass']!=original['mass']:raise ValueError('Checkpoint body changed')
            for key,field in [('positions','position'),('velocities','velocity')]:
                expected=body[field]
                if i==0 and initial_expected is not None:expected=initial_expected[key][j]
                if np.array(expected,dtype='float64').tobytes()!=np.array(values[key][i][j],dtype='float64').tobytes():raise ValueError('Checkpoint/raw state mismatch')
        for j,(s,original) in enumerate(zip(doc['rotations'],initial['rotations'])):
            if {k:v for k,v in s.items() if k not in ('quaternion','angular_momentum')}!={k:v for k,v in original.items() if k not in ('quaternion','angular_momentum')}:raise ValueError('Checkpoint figure changed')
            for key,field in [('quaternions','quaternion'),('spins','angular_momentum')]:
                if np.array(s[field],dtype='float64').tobytes()!=np.array(values[key][i][j],dtype='float64').tobytes():raise ValueError('Checkpoint/raw spin mismatch')
            matrix=Rotation.from_quat(np.roll(s['quaternion'],-1)).as_matrix()
            if matrix.tobytes()!=np.array(values['orientation'][i][j],dtype='float64').tobytes():raise ValueError('Raw orientation inconsistent with quaternion')


def initial_readout(document):
    """Replay only the existing coordinate encoder/decoder, with ZERO RHS calls.

    Continuous t=0 is an observable after a binary64 frame roundtrip; it need
    not be a serializable Experiment(initial==current). Keep the genuine input
    checkpoint and independently validate the separate numerical readout.
    Python here selects no native preparation; no force or solver is called.
    """
    import numpy as np
    from types import SimpleNamespace
    from solar_simulator import nbody_rotation as nb
    from solar_simulator.storage import from_document
    state=from_document(document);original=nb.solve_ivp
    def initial_only(fun,span,y0,**kwargs):return SimpleNamespace(success=True,y=np.repeat(y0[:,None],len(kwargs['t_eval']),axis=1))
    try:
        nb.solve_ivp=initial_only;s=state.settings
        bodies,rotations=nb.integrate(state.bodies,state.rotations,[0.,1.],rtol=s.rtol,position_atol=s.position_atol,velocity_atol=s.velocity_atol,relative_pair=s.relative_pair,backend='python')[0]
    finally:nb.solve_ivp=original
    return dict(positions=[[b.position.x,b.position.y,b.position.z] for b in bodies],velocities=[[b.velocity.x,b.velocity.y,b.velocity.z] for b in bodies])


def load_runtime(role,p,root=ROOT):
    """Canonical imports in a fresh worker; developer dev is never a fallback."""
    if role not in ('baseline','candidate'):raise ValueError('Wrong role')
    owner=p['roles'][role];source=Path(owner['root']).resolve();git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
    if git('rev-parse','HEAD')!=owner['commit'] or git('status','--porcelain'):raise ValueError('Wrong/dirty source commit')
    sys.path.insert(0,str(source/'src'))
    modules={k:importlib.import_module('solar_simulator.'+k) for k in ('experiment','storage','nbody_rotation','recipe','native_forces')}
    import solar_simulator,numpy,scipy,solar_native
    prefix=Path(p['roles']['baseline']['root'])/'.venv'
    require_origins(solar_simulator.__file__,[numpy.__file__,scipy.__file__,solar_native.__file__],source,sys.prefix,prefix)
    expected=json.loads((Path(root)/owner['environment']).read_bytes());require_environment(modules['recipe'].runtime_fingerprint('rust'),expected)
    return modules,dict(role=role,commit=owner['commit'],tree=git('rev-parse','HEAD^{tree}'),source=str(source),environment_LF_SHA256=hashlib.sha256((json.dumps(expected,indent=2)+'\n').encode()).hexdigest(),import_origin=solar_simulator.__file__)


def require_identity(job,p,identity,modules=None):
    role=job.get('role','baseline');owner=p['roles'][role]
    if identity.get('role')!=role or identity.get('commit')!=owner['commit'] or Path(identity.get('source','')).resolve()!=Path(owner['root']).resolve():raise ValueError('Wrong source/job identity')
    expected_env=json.loads((ROOT/owner['environment']).read_bytes())
    digest=hashlib.sha256((json.dumps(expected_env,indent=2)+'\n').encode()).hexdigest()
    if identity.get('role')!=role or identity.get('commit')!=owner['commit'] or Path(identity.get('source','')).resolve()!=Path(owner['root']).resolve() or identity.get('environment_LF_SHA256')!=digest:raise ValueError('Wrong source/environment/job identity')
    if not Path(identity['import_origin']).resolve().is_relative_to(Path(owner['root'])/'src'):raise ValueError('Wrong recorded runtime origin')
    if modules is not None:
        for module in modules.values():
            if not Path(module.__file__).resolve().is_relative_to(Path(owner['root'])/'src'):raise ValueError('Wrong actual runtime module')


@contextmanager
def counters(modules):
    import solar_native
    nb=modules['nbody_rotation'];solve=nb.solve_ivp;compiled=solar_native.point_acceleration
    count=dict(solver_calls=0,RHS=0,nfev=0,compiled_native_calls=0)
    def force(*a,**k):count['compiled_native_calls']+=1;return compiled(*a,**k)
    def observed(fun,*args,**kwargs):
        count['solver_calls']+=1
        def rhs(*a,**k):count['RHS']+=1;return fun(*a,**k)
        result=solve(rhs,*args,**kwargs);count['nfev']+=int(result.nfev);return result
    nb.solve_ivp=observed;solar_native.point_acceleration=force
    try:yield count
    finally:nb.solve_ivp=solve;solar_native.point_acceleration=compiled


def input_document(job,p,root=ROOT):
    """Exact frozen IC and original380 tuning, independently of solver output."""
    root=Path(root)
    if job['case']=='one':
        info=next(x for x in p['physical_inputs']['one_Q2'] if x['backend']==job.get('backend','python'))
        path=root/('.tools/qualification396/inputs/one-'+info['backend']+'.json');require_sha(path,info['file_SHA256']);doc=json.loads(path.read_bytes())
    else:
        info=p['physical_inputs']['two_Q2'];require_sha(root/info['path'],info['sha256']);legacy=json.loads((root/info['path']).read_bytes());doc=next(x['initial'] for x in legacy['cases'] if x['id']==job['case'])
    if job.get('level') not in (None,'legacy394'):
        level=next(x for x in p['levels'] if x['id']==job['level'])
        doc['settings'].update(rtol=level['rtol'],position_atol=level['position_atol'],velocity_atol=level['velocity_atol'])
        for name in ('rotations','initial_rotations'):
            for s in doc[name]:s['quaternion_atol']*=level['spin_factor'];s['momentum_atol']*=level['spin_factor']
    if 'backend' in job:doc['settings']['backend']=job['backend']
    return doc


def initial(job,p,modules,root=ROOT):
    return modules['storage'].from_document(input_document(job,p,root))


def run_job(directory,job,p,modules,identity,*,scope='scientific399',probe_epochs=None):
    """One fixed job; existing complete OR partial directories always refuse."""
    import numpy as np
    if job not in p['jobs']:raise ValueError('Job outside fixed58')
    require_identity(job,p,identity,modules)
    if scope not in ('scientific399','preflight398'):raise ValueError('Wrong scope')
    epochs=job['epochs']
    if scope=='preflight398':
        if probe_epochs is None or probe_epochs!=epochs[:len(probe_epochs)] or len(probe_epochs)<2 or probe_epochs[-1]>125:raise ValueError('Unfixed/long preflight probe')
        epochs=probe_epochs
    elif probe_epochs is not None:raise ValueError('Scientific grid may not be shortened')
    state=initial(job,p,modules);storage=modules['storage'];doc=storage.to_document(state)
    if not p.get('_tool_sources'):raise ValueError('Missing execution tool source binding')
    binding=dict(scope=scope,job=job,source=identity,initial_SHA256=hashlib.sha256(canonical(doc)).hexdigest(),epochs=epochs,contract_SHA256=CONTRACT_SHA,tool_sources_SHA256=p['_tool_sources'])
    directory=Path(directory);directory.mkdir(exist_ok=False);atomic_json(directory/'initial.json',envelope(binding))
    start=perf_counter();cpu=process_time();states=[];records=directory/'states.jsonl.partial'
    try:
        with records.open('xb') as stream:
            def record(sample,*,input_checkpoint=False):
                d=doc if input_checkpoint else storage.to_document(sample);clone=storage.from_document(d)
                if canonical(storage.to_document(clone))!=canonical(d):raise ValueError('Checkpoint roundtrip changed')
                stream.write(canonical(envelope(dict(time=sample.time,document=d,document_role='initial_input' if input_checkpoint else 'physical_checkpoint')))+b'\n');stream.flush();os.fsync(stream.fileno());states.append(sample)
            if job.get('kind')=='reference':
                from scripts.q2_reference397 import reference
                result=reference(doc,epochs,job['rtol']);arrays={k:v.tolist() for k,v in result.items() if k!='RHS'}
                for time in epochs:
                    stream.write(canonical(envelope(dict(time=time,document=None)))+b'\n')
                stream.flush();os.fsync(stream.fileno());count=dict(solver_calls=1,RHS=int(result['RHS']),nfev=int(result['RHS']),compiled_native_calls=0)
            else:
                with counters(modules) as count:
                    if job['recipe']=='cold':
                        record(state)
                        for target in epochs[1:]:
                            state=modules['experiment'].advance(replace(state,settings=replace(state.settings,dt=target-state.time)),1)
                            if state.time!=target:raise ValueError('Cold epoch changed')
                            record(state)
                    else:
                        s=state.settings;samples=modules['nbody_rotation'].integrate(state.bodies,state.rotations,epochs,rtol=s.rtol,position_atol=s.position_atol,velocity_atol=s.velocity_atol,relative_pair=s.relative_pair,backend=s.backend)
                        for i,(time,(b,r)) in enumerate(zip(epochs,samples)):record(replace(state,bodies=tuple(b),rotations=r,time=time),input_checkpoint=i==0)
                from scripts.validate_two_q2_380 import represented
                arrays={k:v.tolist() for k,v in represented(states).items()}
                if count['solver_calls']!=(len(epochs)-1 if job['recipe']=='cold' else 1) or count['RHS']!=count['nfev'] or (count['compiled_native_calls']!=count['RHS'] if job['backend']=='rust' else count['compiled_native_calls']!=0):raise ValueError('Actual recipe/backend/counters mismatch')
        require_arrays(arrays,doc,epochs,runtime=job.get('kind')!='reference')
        os.link(records,directory/'states.jsonl');records.unlink()
        runtime_observables=None
        if job.get('kind')!='reference':
            inv=[modules['nbody_rotation'].invariants(s.bodies,s.rotations) for s in states]
            runtime_observables=dict(E_J=[x[0] for x in inv],P_kg_m_s=[[x[1].x,x[1].y,x[1].z] for x in inv],L_kg_m2_s=[[x[2].x,x[2].y,x[2].z] for x in inv])
        payload=dict(binding=binding,job={k:v for k,v in job.items() if k not in ('role','id')},epochs=epochs,initial=doc,settings=doc['settings'],arrays=arrays,counters=count,runtime_observables=runtime_observables,metrics=None if job.get('kind')=='reference' else drift(arrays,doc,epochs,runtime_observables),CPU_seconds=process_time()-cpu,wall_seconds=perf_counter()-start)
        atomic_json(directory/'result.json',payload)
        files={name:dict(size=(directory/name).stat().st_size,sha256=sha(directory/name)) for name in ('initial.json','result.json','states.jsonl')}
        atomic_json(directory/'complete.json',envelope(dict(binding=binding,files=files,frames=len(epochs))))
        verify_complete(directory,binding)
        return payload
    except BaseException as error:
        failure=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc(),binding=binding)
        try:atomic_json(directory/'failure.json',envelope(failure))
        except Exception as save_error:
            print(failure['traceback'],file=sys.stderr)
            print('Failure receipt could not be saved: '+repr(save_error),file=sys.stderr)
        raise


def assess_all(results,p):
    """Reuse380 difference/drift definitions; reject missing/mixed input, never skip."""
    import numpy as np
    expected={j['id'] for j in p['jobs']}
    if p['jobs']!=contract()['jobs']:raise ValueError('Changed58-job contract')
    if set(results)!=expected:raise ValueError('Full58results required')
    equivalence=[];criteria=[];references={};convergence=[]
    for job in p['jobs']:
        r=results[job['id']]
        if r['binding']['scope']!='scientific399' or r['binding']['job']!=job or r['epochs']!=job['epochs'] or r['binding'].get('contract_SHA256')!=CONTRACT_SHA:raise ValueError('Wrong/mixed scientific job/protocol')
        require_identity(job,p,r['binding']['source'])
        if r['binding'].get('tool_sources_SHA256')!=p['_tool_sources']:raise ValueError('Wrong observer/executor source binding')
        if canonical(r['initial'])!=canonical(input_document(job,p)):raise ValueError('Scientific IC/settings mismatch')
        if r['binding']['initial_SHA256']!=hashlib.sha256(canonical(r['initial'])).hexdigest():raise ValueError('Changed scientific IC')
        require_arrays(r['arrays'],r['initial'],r['epochs'],runtime=job.get('kind')!='reference')
        if job.get('kind')!='reference':
            validate_documents(r)
            c=r['counters']
            if any(type(c.get(k)) is not int or c[k]<1 for k in ('solver_calls','RHS','nfev')) or c['solver_calls']!=(len(r['epochs'])-1 if job['recipe']=='cold' else 1) or c['RHS']!=c['nfev'] or c['compiled_native_calls']!=(c['RHS'] if job['backend']=='rust' else 0):raise ValueError('Invalid actual recipe/backend counters')
        if job.get('kind')=='reference':references[job['rtol']]=r['arrays']
    for job in p['jobs']:
        r=results[job['id']]
        if job.get('kind')=='reference':continue
        if job['role']=='baseline':
            other=dict(job,role='candidate',id=job['id'].replace('baseline__','candidate__',1));e=source_equivalence(r,results[other['id']]);equivalence.append(dict(job=job['id'],**e))
        if job['case']=='one':ref0,ref1=references[3e-11],references[3e-13];limits=p['one_Q2_criteria']
        else:
            info=p['reference_policy']['two_Q2'];require_sha(ROOT/info['npz'],info['sha256'])
            with np.load(ROOT/info['npz'],allow_pickle=False) as z:
                refs=[{k.split('__')[-1]:z[k] for k in z.files if k.startswith(job['case']+'__reference'+str(i)+'__')} for i in (0,1)]
            ref0,ref1=refs;limits=p['criteria']
        gap=difference(ref0,ref1,r['initial'],r['epochs']);error=difference(r['arrays'],ref1,r['initial'],r['epochs']);m=drift(r['arrays'],r['initial'],r['epochs'],r['runtime_observables'])
        failed=[k for k in ('energy_drift','angular_drift','linear_drift','quaternion_norm') if m[k]>=limits[k]]
        if max(gap.values())>=1e-8:failed.append('reference_uncertainty')
        if job['case']=='one':
            if error['position']>=limits['position_reference_normalized'] or error['orientation']>=limits['orientation_Frobenius']:failed.append('one_reference')
        elif job['level']=='fine' and max(error.values())>=p['criteria']['reference_difference']:failed.append('fine_reference')
        criteria.append(dict(job=job['id'],drift=m,reference_difference=error,reference_uncertainty=gap,failed=failed))
        if job.get('level')=='standard':
            find=lambda level:next(results[j['id']] for j in p['jobs'] if all(j.get(k)==job.get(k) for k in ('role','backend','case','recipe')) and j.get('level')==level)
            cf=difference(find('coarse')['arrays'],find('fine')['arrays'],r['initial'],r['epochs']);sf=difference(r['arrays'],find('fine')['arrays'],r['initial'],r['epochs'])
            convergence.append(dict(job=job['id'],coarse_fine=cf,standard_fine=sf,strict_pass=max(sf.values())<max(cf.values())))
    return dict(source_equivalence_status='PASS' if all(x['exact'] for x in equivalence) else 'FAIL',scientific_criteria_status='FAIL' if any(x['failed'] for x in criteria) or any(not x['strict_pass'] for x in convergence) else 'PASS',reference_resolution_status='FAIL' if any('reference_uncertainty' in x['failed'] for x in criteria) else 'EMPIRICAL_LEVEL_GAP_PASS_NOT_GLOBAL_BOUND',release_readiness='NO-GO',source_equivalence=equivalence,scientific_criteria=criteria,strict_convergence=convergence,scope='Separate verdicts; no rigorous global-errorbound, no releasewaiver')
