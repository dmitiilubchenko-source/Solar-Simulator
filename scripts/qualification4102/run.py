"""Targeted launcher checks, then one frozen bounded regression set."""
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys,time
from unittest.mock import patch
from . import monitor as m

W=Path('C:/Users/Admin/Documents/Codex/Solar4102-20261118/attempt2')
PROBE=Path(__file__).with_name('probe.py').resolve()


def valid(path,sha):
    r=json.loads(Path(path).read_bytes())
    if r['monitor_SHA256']!=sha or r['complete'] is not True or r['error'] or r['exit_code']!=0 or r['final_job']['active']!=0 or r['worker_CPU_seconds'] is None:
        raise ValueError('Non-admissible receipt')
    return r


def run():
    W.mkdir(exist_ok=False)
    start=time.perf_counter();parent=time.process_time();rows=[]
    limits=dict(cpu_seconds=10,wall_seconds=8,private_bytes=512*1024**2,disk_bytes=8*1024**2)
    sha=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
    cases=[('echo','echo',None,None),('gui','gui',None,None),('root0','echo',None,None),('orphan','orphan','unexpected-owned-descendant',None),('grand','grand','unexpected-owned-descendant',None),('joined','joined',None,None),('short','grand','unexpected-owned-descendant',None),('nonzero','nonzero','root-nonzero',None),('crash','crash','root-nonzero',None),('wall','sleep','stage-wall',('wall_seconds',.4)),('cpu','burn','stage-CPU',('cpu_seconds',.3)),('memory','burn','private-memory',('private_bytes',1024)),('disk','disk','stage-disk',('disk_bytes',1024)),('interrupt','burn','interrupted','interrupt'),('assign','echo','monitor-error','assign'),('resume','echo','monitor-error','resume'),('create','echo','monitor-error','create'),('access','burn','monitor-error','access'),('cleanup','orphan','unexpected-owned-descendant','cleanup'),('finalcpu','echo','final-accounting-unresolved','finalcpu'),('receipt','echo',None,'receipt')]
    m.save(W/'frozen-regression-plan.json',dict(cases=cases,source_sha=sha,probe_sha=hashlib.sha256(PROBE.read_bytes()).hexdigest(),budget=limits,scope='Targeted launcher echo/gui then one frozen regression; old suites not repeated'))
    for name,mode,reason,fault in cases:
        case=W/(name+' output Юникод');case.mkdir();lim=limits.copy();kw={};hook=None;target=None;replacement=None
        if isinstance(fault,(tuple,list)):lim[fault[0]]=fault[1]
        if fault=='interrupt':
            def hook(s):raise KeyboardInterrupt('injected')
        if fault in ('assign','create','resume','cleanup','receipt'):
            target={'assign':'assign','create':'create','resume':'resume','cleanup':'terminate_job','receipt':'save'}[fault]
            def replacement(*a):raise OSError('injected '+str(fault))
        if fault=='access':
            target='process_handle'
            def replacement(*a):raise PermissionError('injected AccessDenied')
        if fault=='finalcpu':
            target='accounting';original=m.accounting
            def replacement(job):
                r=original(job)
                if r['active']==0:raise OSError('injected missing final CPU')
                return r
        cmd=[sys.executable,'-I','-B',str(PROBE),mode,str(case),'Русский пробел','quote"arg','trailing\\']
        rec=None;err=None
        try:
            if target:
                with patch.object(m,target,replacement):rec=m.monitor(cmd,case/'guard',case,lim,cwd=case,env={**os.environ,'PYTHONPATH':'unwanted','PYTHONHOME':'unwanted'},hook=hook)
            else:rec=m.monitor(cmd,case/'guard',case,lim,cwd=case,hook=hook)
        except BaseException as exc:err=dict(type=type(exc).__name__,message=str(exc))
        if rec:
            ok=rec['complete']==(reason is None) and rec['limit_reason']==reason
            if name=='echo':
                log=(case/'guard/stdout.log').read_text(encoding='utf8');data=json.loads(log.splitlines()[0]);ok=ok and data['argv']==cmd[-3:] and data['stdin']=='' and data['env']['PYTHONPATH'] is None and data['env']['PYTHONHOME'] is None and all(data['env'][x]=='1' for x in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')) and 'stderr-token' in log
            if name=='gui':ok=ok and 'tk-clean' in (case/'guard/stdout.log').read_text()
        else:ok=name=='receipt' and err is not None and not (case/'guard/supervisor.json').exists()
        rows.append(dict(name=name,expected_reason=reason,contract_check=ok,record=rec,external_error=err))
        m.save(case/'test-result.json',rows[-1]);print(name,ok,rec and rec['limit_reason'],flush=True)
    m.save(W/'suite.json',dict(rows=rows,parent_CPU=time.process_time()-parent,wall=time.perf_counter()-start))


if __name__=='__main__':run()
