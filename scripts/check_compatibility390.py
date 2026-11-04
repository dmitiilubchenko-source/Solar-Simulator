"""One backward-format rejection check, without any orbit integration.

Uses frozen389 inputs; genuine candidate validates the two-figure document,
then genuine032 rejects it through storage and the normal GUI error handler.
"""
from contextlib import contextmanager,ExitStack
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import threading


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,allow_nan=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


def canonical(value):return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))


def audit_document(value):
    if value.get('schema_version')!=10 or value.get('origin') is not None:raise ValueError('Expected self-contained schema10')
    for field in ('rotations','initial_rotations'):
        if len(value[field])!=2 or len({s['body'] for s in value[field]})!=2:raise ValueError('Two distinct figures required')
        for state in value[field]:
            for name,size in (('quaternion',4),('angular_momentum',3)):
                if len(state[name])!=size or any(type(x) not in (int,float) or not math.isfinite(x) for x in state[name]):raise ValueError('Invalid q/S')
    def walk(x):
        if isinstance(x,dict):
            for item in x.values():walk(item)
        elif isinstance(x,list):
            for item in x:walk(item)
        elif isinstance(x,str) and ('://' in x or x.startswith('\\\\') or re.match(r'^[A-Za-z]:[\\/]',x)):
            raise ValueError('External reference/path not allowed')
    walk(value)


def rotation_bits(document):
    return [(field,s['body'],b''.join(struct.pack('>d',float(n)) for name in ('quaternion','angular_momentum') for n in s[name]).hex())
            for field in ('initial_rotations','rotations') for s in document.get(field,[])]


def configure():
    os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    for key in ('VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','PYTHONHASHSEED'):os.environ.pop(key,None)


def load_helper(root):
    spec=importlib.util.spec_from_file_location('_memory388',root/'scripts/check_startup_memory388.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);return module


@contextmanager
def memory_guard(helper,out):
    stop=threading.Event();stats=dict(peak_private_bytes=0,samples=0,limit_private_bytes=450*1024**2,poll_seconds=.01)
    def sample():
        m=helper.windows_memory();stats['peak_private_bytes']=max(stats['peak_private_bytes'],m['PrivateUsage']);stats['samples']+=1
        if m['PrivateUsage']>stats['limit_private_bytes']:
            save(out/'self-stop.json',dict(reason='private-memory',windows=m));os._exit(90)
    def run():
        try:
            while not stop.wait(.01):sample()
        except BaseException as error:
            save(out/'self-error.json',dict(error=repr(error)));os._exit(91)
    sample();thread=threading.Thread(target=run,daemon=True);thread.start()
    try:yield
    finally:
        stop.set();thread.join(timeout=2);sample();save(out/'self-memory.json',stats)


def runtime(root,candidate,portable):
    if candidate:sys.path[:0]=[str(candidate/'src'),str(candidate)]
    import solar_simulator,solar_native,numpy,scipy
    from solar_simulator.recipe import runtime_fingerprint
    prefix=(candidate/'.venv') if candidate else portable/'runtime'
    package=(candidate/'src') if candidate else prefix/'Lib/site-packages'
    assert Path(sys.prefix).resolve()==prefix.resolve()
    assert Path(solar_simulator.__file__).resolve().is_relative_to(package.resolve())
    for module in (solar_native,numpy,scipy):assert Path(module.__file__).resolve().is_relative_to(prefix.resolve())
    native=getattr(solar_native,'solar_native',solar_native)
    expected=('651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091' if candidate else '0cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601')
    assert sha(native.__file__)==expected
    return runtime_fingerprint,dict(prefix=sys.prefix,executable=sys.executable,package=solar_simulator.__file__,
        native_path=native.__file__,native_SHA256=expected,numpy=numpy.__version__,scipy=scipy.__version__)


def check(args):
    configure();out=args.output;out.mkdir(exist_ok=False);helper=load_helper(args.project)
    with memory_guard(helper,out):
        from_input=json.loads(args.input.read_text('utf-8'));audit_document(from_input)
        assert sha(args.input)==args.expected_sha
        if args.candidate:sys.path[:0]=[str(args.candidate/'src'),str(args.candidate)]
        from solar_simulator.storage import load,to_document
        fpfunc,binding=runtime(args.project,args.candidate,args.portable)
        if args.candidate:
            state=load(args.input);document=to_document(state)
            assert canonical(document)==canonical(from_input) and rotation_bits(document)==rotation_bits(from_input)
            fp=fpfunc('rust');assert fp==json.loads(args.expected_environment.read_text('utf-8'))
            save(out/'environment.json',fp);save(out/'runtime.json',binding)
            save(out/'result.json',dict(valid_schema=10,figures=2,both_initial_current_qS_preserved=True,
                input_SHA256=sha(args.input),document_canonical_SHA256=hashlib.sha256(canonical(document).encode()).hexdigest(),integration_calls=0))
            return
        # Only old GUI needs Matplotlib/Tk. No integration function may run.
        import tkinter as tk
        import solar_simulator.app as appmod
        import solar_simulator.experiment as experiment
        import solar_simulator.accuracy as accuracy
        import solar_simulator.nbody_rotation as rotation
        from solar_simulator.recovery import save_recovery,recovery_directory
        from unittest.mock import patch
        fp_before=fpfunc('rust');assert fp_before==json.loads(args.expected_environment.read_text('utf-8'))
        save(out/'environment-start.json',fp_before);save(out/'runtime.json',binding)
        blas=helper.loaded_blas();assert {x['package'] for x in blas}=={'numpy','scipy'} and all(x['threads']==1 for x in blas)
        save(out/'BLAS.json',blas)
        try:unexpected=load(args.input)
        except ValueError as error:direct_error=str(error)
        else:
            details=dict(error='Old032 accepted newtwoQ2',rotations=len(unexpected.rotations),initial_rotations=len(unexpected.initial_rotations))
            try:details['document']=to_document(unexpected)
            except Exception as error:details['serialization_error']=repr(error)
            save(out/'unexpected-direct-acceptance.json',details)
            raise AssertionError('Old032 accepted unsupportedfile')
        assert direct_error=='Схема 10 требует одну динамическую фигуру'
        baseline=load(args.baseline);before=to_document(baseline);assert len(before['rotations'])==1
        root=tk.Tk();root.withdraw();lab=appmod.Laboratory(root,baseline)
        errors=[];calls=[]
        def forbidden(*a,**k):calls.append('integration');raise AssertionError('Integration forbidden in390')
        tree=lambda:{str(p.relative_to(recovery_directory())):sha(p) for p in recovery_directory().rglob('*') if p.is_file()}
        recovery_before=tree();original=lab.experiment;settings=lab.experiment.settings;parent=lab.parent_snapshot
        try:
            with ExitStack() as stack:
                for owner,name in ((experiment,'advance'),(appmod,'advance'),(accuracy,'evolve_accurate'),(rotation,'integrate')):
                    stack.enter_context(patch.object(owner,name,side_effect=forbidden))
                stack.enter_context(patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(args.input)))
                stack.enter_context(patch('solar_simulator.app.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)))
                lab._guard(lab._load)  # actual button handler and normal error-reporting route
            after=to_document(lab.experiment);recovery_after=tree()
            save(out/'before.json',before);save(out/'after.json',after)
            assert len(errors)==1 and errors[0][0]=='Расчёт не выполнен' and errors[0][1]==direct_error
            assert lab.experiment is original and lab.experiment.settings==settings and lab.parent_snapshot==parent
            assert canonical(before)==canonical(after) and rotation_bits(before)==rotation_bits(after)
            assert recovery_before==recovery_after and not calls
            # Explicit post-refusal save/recovery must contain the original ONE figure.
            with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(out/'post-error-save.json')):lab._save()
            saved=load(out/'post-error-save.json');assert canonical(to_document(saved))==canonical(before)
            recovery=save_recovery(lab.experiment,reason='stopped')
            restored=load(recovery);assert canonical(to_document(restored))==canonical(before)
            save(out/'result.json',dict(rejected=True,direct_error=direct_error,GUI_error=[list(x) for x in errors],
                state_identity_preserved=True,settings_parent_preserved=True,document_unchanged=True,qS_bits_preserved=True,
                recovery_unchanged_during_refusal=True,post_error_save_valid=True,post_error_recovery_valid=True,
                recovery_path=str(recovery),input_SHA256=sha(args.input),baseline_SHA256=sha(args.baseline),integration_calls=len(calls)))
        finally:lab.close()
        fp_after=fpfunc('rust');assert fp_after==fp_before
        save(out/'environment-end.json',fp_after)
        assert sha(args.input)==args.expected_sha


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('project','portable','input','baseline','output','expected-environment'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate',type=Path);p.add_argument('--expected-sha',required=True)
    check(p.parse_args())


if __name__=='__main__':main()
