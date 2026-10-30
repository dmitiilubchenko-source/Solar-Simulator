"""Observe existing376 production jobs for a separately frozen Git candidate.

This command adds provenance, call counters and recoverable packet journals.
It neither supplies a solver nor changes force arithmetic or acceptance rules.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import sys

TOOL_ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path,value):
    with Path(path).open('x',encoding='utf8',newline='\n') as stream:
        json.dump(value,stream,indent=2,allow_nan=False)
        stream.write('\n')


def verify_freeze(candidate,freeze_path,protocol_path):
    from scripts.release_history import evidence_path
    from solar_simulator.recipe import runtime_fingerprint
    from solar_simulator.simulation import G
    import solar_simulator,scipy,numpy,solar_native
    candidate=Path(candidate).resolve();freeze=read(freeze_path)
    def git(*args):
        return subprocess.check_output(['git','-C',str(candidate),*args],text=True).strip()
    if git('rev-parse','HEAD')!=freeze['candidate_commit'] or git('status','--porcelain'):
        raise ValueError('Candidate Git commit/tree changed')
    if sha(protocol_path)!=freeze['protocol_SHA256']:
        raise ValueError('Frozen protocol SHA256 mismatch')
    for name,digest in freeze['source_SHA256'].items():
        if sha(evidence_path(candidate,name))!=digest:
            raise ValueError('Candidate source changed: '+name)
    for name,digest in freeze['tool_SHA256'].items():
        if sha(evidence_path(TOOL_ROOT,name))!=digest:
            raise ValueError('Observer tool changed: '+name)
    environment=evidence_path(Path(freeze_path).parent,freeze['environment_file'])
    if sha(environment)!=freeze['environment_SHA256'] or runtime_fingerprint('rust')!=read(environment):
        raise ValueError('Actual candidate environment changed')
    if not Path(solar_simulator.__file__).resolve().is_relative_to(candidate/'src'):
        raise ValueError('Wrong production runtime imported')
    prefix=(candidate/'.venv').resolve()
    if Path(sys.prefix).resolve()!=prefix:
        raise ValueError('Wrong interpreter environment')
    for module in (scipy,numpy,solar_native):
        if not Path(module.__file__).resolve().is_relative_to(prefix):
            raise ValueError('Mixed dependency/native installation')
    if G.hex()!=freeze['G_hex']:
        raise ValueError('Gravitational constant changed')
    return freeze


@contextmanager
def observe(journal):
    """Return original results unchanged; include resume calls in all counters."""
    import numpy as np
    from scripts import check_runtime_reliability376 as driver
    from solar_simulator import accuracy,native_forces
    from solar_simulator.error_control import PerBodyDOP853
    from solar_simulator.storage import to_document
    original_seed,original_advance=driver.seed_from,driver.advance
    original_solve,original_prepare=accuracy.solve_ivp,native_forces.prepare
    rows={};active=[None]
    def emit(value):
        journal.write(json.dumps(value,allow_nan=False,separators=(',',':'))+'\n')
        journal.flush()
    def seed(case,job):
        active[0]=job['id']
        if job['id'] in rows:raise ValueError('Repeated scientific job')
        rows[job['id']]=dict(job=job,solver_calls=0,nfev=0,native_force_calls=0,advance_calls=0,
            method='solar_simulator.error_control.PerBodyDOP853',internal_steps_known=False)
        result=original_seed(case,job)
        emit(dict(job=active[0],kind='initial',document=to_document(result)))
        return result
    def advance(state,*args,**kwargs):
        result=original_advance(state,*args,**kwargs)
        rows[active[0]]['advance_calls']+=1
        emit(dict(job=active[0],kind='completed_packet',input_time_seconds=state.time,
            document=to_document(result)))
        return result
    def solve(*args,**kwargs):
        row=rows[active[0]]
        if (kwargs.get('method') is not PerBodyDOP853 or
                kwargs.get('max_step',float('inf'))!=float('inf')):
            raise ValueError('Expected unchanged production PerBodyDOP853 without step cap')
        if kwargs['rtol']!=row['job']['rtol']:
            raise ValueError('Unexpected solver tolerance')
        atol=np.asarray(kwargs['atol'])
        if atol.shape!=(12,) or not np.array_equal(atol,np.r_[np.full(6,1e-3),np.full(6,1e-9)]):
            raise ValueError('Unexpected absolute tolerance/layout')
        result=original_solve(*args,**kwargs)
        row['solver_calls']+=1;row['nfev']+=int(result.nfev)
        return result
    def prepare(*args,**kwargs):
        force=original_prepare(*args,**kwargs)
        def counted(*a,**k):
            rows[active[0]]['native_force_calls']+=1
            return force(*a,**k)
        return counted
    driver.seed_from,driver.advance=seed,advance
    accuracy.solve_ivp,native_forces.prepare=solve,prepare
    try:
        yield rows
    finally:
        driver.seed_from,driver.advance=original_seed,original_advance
        accuracy.solve_ivp,native_forces.prepare=original_solve,original_prepare


def array_read_guard(stage):
    """Scientific acquisition may not import historical trajectory arrays."""
    stage=Path(stage).resolve()
    def audit(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes)):
            return
        path=Path(args[0].decode() if isinstance(args[0],bytes) else args[0])
        mode=args[1] if len(args)>1 else None
        if path.suffix=='.npz' and isinstance(mode,str) and 'r' in mode:
            if not path.resolve().is_relative_to(stage):
                raise ValueError('Historical arrays forbidden during acquisition')
    return audit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--freeze',type=Path,required=True)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();candidate=args.candidate.resolve();output=args.output.resolve()
    if output.exists():raise FileExistsError('Preserve existing scientific output')
    if any((output.parent/name).exists() for name in ('packet-journal.jsonl','execution-trace.json')):
        raise FileExistsError('Preserve existing scientific journal/trace')
    sys.path[:0]=[str(candidate/'src'),str(candidate)]
    from scripts import check_runtime_reliability376 as driver
    if driver.ROOT.resolve()!=candidate:raise ValueError('Wrong376 driver imported')
    freeze=verify_freeze(candidate,args.freeze,args.protocol)
    journal_path=output.parent/'packet-journal.jsonl';failure=None;rows={}
    sys.addaudithook(array_read_guard(output.parent))
    try:
        with journal_path.open('x',encoding='utf8',newline='\n') as journal,observe(journal) as rows:
            driver.run(output,protocol_path=args.protocol,expected_sha=freeze['protocol_SHA256'])
        jobs=read(args.protocol)['jobs']
        if list(rows)!=[j['id'] for j in jobs]:raise ValueError('Missing acquired jobs')
        for job in jobs:
            row=rows[job['id']]
            if row['solver_calls']<=0 or row['nfev']<=0:
                raise ValueError('Production solver was not executed')
            if row['native_force_calls']!=(row['nfev'] if job['backend']=='rust' else 0):
                raise ValueError('Actual native force calls differ from backend/RHS')
    except BaseException as error:
        failure=dict(type=type(error).__name__,message=str(error))
        raise
    finally:
        try:verify_freeze(candidate,args.freeze,args.protocol);unchanged=True
        except BaseException as error:
            unchanged=False
            if failure is None:failure=dict(type=type(error).__name__,message=str(error))
        write(output.parent/'execution-trace.json',dict(candidate_commit=freeze['candidate_commit'],
            freeze_SHA256=sha(args.freeze),protocol_SHA256=sha(args.protocol),jobs=rows,
            solver_executed=bool(rows),complete=failure is None,source_environment_unchanged=unchanged,
            failure=failure,journal_SHA256=sha(journal_path),
            counts_include_same_packet_restart=True,current_runtime_qualified=False))
        if not unchanged:raise ValueError('Candidate changed during acquisition')


if __name__=='__main__':
    main()
