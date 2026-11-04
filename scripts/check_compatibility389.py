"""Bounded comparison harness/observer, without production code changes.

Acquisition uses the audited local successor of the SHA-preserved 388 worker.
The observer reads JSON states and imports no Solar numerical evaluator.
"""
import argparse
from collections import Counter
import ctypes as ct
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import threading
from time import perf_counter


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text('utf-8'))


def save(path,data):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(data,f,ensure_ascii=False,allow_nan=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


def install_profile():
    os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    for key in ('VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','PYTHONHASHSEED'):os.environ.pop(key,None)


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class SelfGuard:
    def __init__(self,helper,output):
        self.helper=helper;self.output=output;self.done=threading.Event();self.peak=0;self.samples=0;self.error=None
    def sample(self):
        m=self.helper.windows_memory();self.peak=max(self.peak,m['PrivateUsage']);self.samples+=1
        if m['PrivateUsage']>900*1024**2:
            save(self.output/'self-stop.json',dict(reason='private-memory',pid=os.getpid(),windows=m))
            os._exit(90)
    def run(self):
        try:
            while not self.done.wait(.01):self.sample()
        except BaseException as error:
            self.error=repr(error)
            save(self.output/'self-error.json',dict(error=self.error));os._exit(91)
    def __enter__(self):
        self.sample();self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start();return self
    def __exit__(self,*args):
        self.done.set();self.thread.join(timeout=2);self.sample()
        save(self.output/'self-memory.json',dict(peak_private_bytes=self.peak,samples=self.samples,poll_seconds=.01,
             limitations='Sampled private commit, not OS quota; synchronous boundary samples plus10ms background; short spikes possible.'))


def runtime_binding(args,helper):
    if args.candidate:
        sys.path[:0]=[str(args.candidate/'src'),str(args.candidate)]
    import solar_simulator,numpy,scipy,matplotlib,solar_native
    import solar_simulator.accuracy,solar_simulator.nbody_rotation,solar_simulator.app
    from solar_simulator.recipe import runtime_fingerprint
    expected_prefix=(args.candidate/'.venv') if args.candidate else args.portable/'runtime'
    expected_package=(args.candidate/'src') if args.candidate else expected_prefix/'Lib/site-packages'
    if Path(sys.prefix).resolve()!=expected_prefix.resolve():raise ValueError('Wrong interpreter prefix')
    if not Path(solar_simulator.__file__).resolve().is_relative_to(expected_package.resolve()):raise ValueError('Wrong runtime package')
    for module in (numpy,scipy,matplotlib,solar_native):
        if not Path(module.__file__).resolve().is_relative_to(expected_prefix.resolve()):raise ValueError('Mixed installation')
    native=getattr(solar_native,'solar_native',solar_native)
    expected=('651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091' if args.candidate else
              '0cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601')
    if sha(native.__file__)!=expected:raise ValueError('Actual native SHA mismatch')
    fp=runtime_fingerprint('rust')
    if list(fp['numerical_environment'].values())!=['1','1','1',None,None,None]:raise ValueError('Wrong numerical profile')
    blas=helper.loaded_blas()
    if {x['package'] for x in blas}!={'numpy','scipy'} or any(x['threads']!=1 for x in blas):raise ValueError('BLAS threads not verified')
    kernel=ct.WinDLL('kernel32');get=kernel.GetModuleHandleW;get.argtypes=[ct.c_wchar_p];get.restype=ct.c_void_p
    filename=kernel.GetModuleFileNameW;filename.argtypes=[ct.c_void_p,ct.c_wchar_p,ct.c_uint];filename.restype=ct.c_uint
    for entry in blas:
        buf=ct.create_unicode_buffer(32768)
        if not filename(get(entry['dll']),buf,len(buf)):raise ct.WinError()
        path=Path(buf.value).resolve()
        if not path.is_relative_to(expected_prefix.resolve()):raise ValueError('Mixed loaded BLAS DLL')
        entry.update(path=str(path),SHA256=sha(path))
    return fp,dict(prefix=sys.prefix,executable=sys.executable,package=solar_simulator.__file__,
        numpy=numpy.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,python=fp['python'],
        native_path=native.__file__,native_SHA256=expected,BLAS=blas)


def verify_candidate(args):
    if args.candidate:
        m=load_module('_frozen384',args.developer_root/'scripts/qualify_newton384.py')
        m.verify_freeze(args.candidate,args.developer_root/'.tools/qualification385/retry/freeze.json',
                        args.developer_root/'.tools/qualification385/retry/protocol.json')


def acquire(args):
    install_profile()
    output=args.root/('harness-'+args.phase+'-'+args.label);output.mkdir(exist_ok=False)
    helper=load_module('_memory388',args.developer_root/'scripts/check_startup_memory388.py')
    draft=load_module('_acquisition389',args.draft)
    counts={};active=None;array_opens=[]
    def audit(event,data):
        if event=='open' and data and isinstance(data[0],(str,bytes)):
            path=os.fsdecode(data[0])
            if Path(path).suffix.lower() in ('.npz','.npy'):
                array_opens.append(path);raise RuntimeError('Scientific array file forbidden during acquisition')
    sys.addaudithook(audit)
    def profiler(frame,event,arg):
        nonlocal active
        name=frame.f_code.co_name;filename=frame.f_code.co_filename.replace('\\','/')
        if name=='advance' and filename.endswith('/solar_simulator/experiment.py'):
            if event=='call':
                parent=frame.f_back;case=parent.f_locals.get('case') if parent and parent.f_code.co_name=='worker' else None
                active=case['id'] if isinstance(case,dict) else None
                if active:counts.setdefault(active,Counter())['advance']+=1
            elif event=='return':active=None
        if active:
            if event=='call' and name=='rhs' and filename.endswith(('/accuracy.py','/nbody_rotation.py')):counts[active]['Python_RHS']+=1
            if event=='call' and name=='step' and filename.endswith('/simulation.py'):counts[active]['Python_Verlet']+=1
            if event=='c_call' and str(getattr(arg,'__module__','')).startswith('solar_native'):
                counts[active]['native_'+getattr(arg,'__name__','unknown')]+=1
    with SelfGuard(helper,output):
        before,binding=runtime_binding(args,helper);verify_candidate(args)
        save(output/'environment-start.json',before);save(output/'runtime-binding.json',binding)
        try:
            if args.phase=='startup':pass
            elif args.phase=='prepare':draft.prepare(args.root)
            elif args.phase=='worker':
                sys.setprofile(profiler)
                try:draft.worker(args.root,args.label,args.candidate,args.developer_root)
                finally:sys.setprofile(None)
            elif args.phase=='old-two':draft.reject_two(args.root)
        finally:
            after,end=runtime_binding(args,helper)
            save(output/'environment-end.json',after)
            save(output/'backend-calls.json',dict(cases=counts,array_file_opens=array_opens,method='Python profile events and actual PyO3 c_call; no numerical function replacement'))
            stable=before==after and binding==end
            save(output/'environment-stability.json',dict(stable=stable,canonical_fingerprint_SHA256=canonical_sha(before)))
            if not stable:raise ValueError('Runtime/environment changed during phase')
            verify_candidate(args)


def observe(args):
    observer=load_module('_observer387',args.developer_root/'scripts/check_compatibility387.py')
    observer.observe(args.root)
    rows=read(args.root/'comparison.json')['cases'];plan=read(args.root/'plan.json')
    for case,row in zip(plan['cases'],rows):
        a=read(args.root/'accepted'/case['id']/'frames.json');b=read(args.root/'candidate'/case['id']/'frames.json')
        row['max_delta_E_J']=max(abs(t['accepted']['E_J']-t['candidate']['E_J']) for t in row['invariants'])
        for name,field in [('P_kg_m_s','max_delta_P_kg_m_s'),('L_kg_m2_s','max_delta_L_kg_m2_s')]:
            row[field]=max(math.dist(t['accepted'][name],t['candidate'][name]) for t in row['invariants'])
        row['rotations']=[]
        for x,y in zip(a,b):
            assert len(x.get('rotations',[]))==len(y.get('rotations',[]))
            for rx,ry in zip(x.get('rotations',[]),y.get('rotations',[])):
                assert rx['body']==ry['body']
                row['rotations'].append(dict(time_seconds=x['time'],body=rx['body'],raw_q_difference=math.dist(rx['quaternion'],ry['quaternion']),
                    S_difference_kg_m2_s=math.dist(rx['angular_momentum'],ry['angular_momentum'])))
        row['restart_bits']={}
        for label in ('accepted','candidate'):
            resume=read(args.root/label/case['id']/'resume.json');final=read(args.root/label/case['id']/'frames.json')[-1]
            row['restart_bits'][label]=observer.state_bytes(resume)==observer.state_bytes(final)
        for label in ('accepted','candidate'):
            calls=read(args.root/('harness-worker-'+label)/'backend-calls.json')['cases'].get(case['id'],{})
            native=sum(v for k,v in calls.items() if k.startswith('native_'))
            assert calls.get('advance')==5,(label,case['id'],calls)
            if case['id'].endswith('-rust'):assert native>0,(case['id'],calls)
            else:assert native==0 and calls.get('Python_RHS',calls.get('Python_Verlet',0))>0,(case['id'],calls)
    save(args.root/'independent-comparison.json',dict(cases=rows,inputs_unchanged=observer.tree(args.root/'inputs')==plan['inputs_SHA256'],
        physical_accuracy_claim=False,reference='Other genuine version on identical short cases, not analytical/JPL accuracy reference'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',required=True,choices=['startup','prepare','worker','old-two','observe'])
    p.add_argument('--root',type=Path,required=True);p.add_argument('--developer-root',type=Path,required=True)
    p.add_argument('--draft',type=Path);p.add_argument('--label',choices=['accepted','candidate']);p.add_argument('--portable',type=Path)
    p.add_argument('--candidate',type=Path);a=p.parse_args()
    if a.phase=='observe':observe(a)
    else:acquire(a)


if __name__=='__main__':main()
