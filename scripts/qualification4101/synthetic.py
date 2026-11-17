"""Bounded synthetic probes. This runner never imports Solar runtime."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
from unittest.mock import patch
import psutil
from . import monitor as m

W=Path('C:/Users/Admin/Documents/Codex/Solar4101-20261117/attempt4')
MODULE='scripts.qualification4101.synthetic'


def validate(path,sha):
    r=json.loads(Path(path).read_bytes())
    if not r['complete'] or r['monitor_SHA256']!=sha or r['final_job']['active'] or r['worker_CPU_seconds'] is None or any(p['alive'] for p in r['processes']):
        raise ValueError('Receipt not admissible')
    return r


def worker(mode):
    with (Path(sys.argv[3])/(str(os.getpid())+'.pid.json')).open('x') as f:
        json.dump(dict(pid=os.getpid(),creation_time=psutil.Process().create_time(),mode=mode),f)
    cmd=[sys.executable,'-X','utf8','-B','-m',MODULE,'worker']
    if mode in ('orphan','grandchild','short-parent'):
        subprocess.Popen(cmd+(['short-parent'] if mode=='grandchild' else ['burn'])+[sys.argv[3]])
        time.sleep(.5 if mode!='short-parent' else .02)
    elif mode=='joined':
        subprocess.run(cmd+['quick',sys.argv[3]],check=True);time.sleep(.3)
    elif mode=='burn':
        end=time.perf_counter()+3;data=bytearray(16*1024**2)
        while time.perf_counter()<end:sum(range(5000))
    elif mode=='nonzero':raise SystemExit(7)
    elif mode=='crash':os._exit(9)
    elif mode=='disk':
        (Path(sys.argv[3])/'payload.bin').write_bytes(bytes(2*1024**2));time.sleep(2)
    elif mode=='sleep':time.sleep(2)
    elif mode=='old':
        # The outer new Job owns the entire reproducer, including any orphan.
        cmd=[sys.executable,'-X','utf8','-B','-m',MODULE,'worker','orphan',sys.argv[3]]
        rec=m.old.monitor(cmd,Path(sys.argv[3])/'original-monitor',Path(sys.argv[3]),dict(cpu_seconds=10,wall_seconds=8,private_bytes=512*1024**2,disk_bytes=8*1024**2))
        live=[]
        for p in rec['processes']:
            try:
                q=psutil.Process(p['pid'])
                if q.create_time()==p['creation_time'] and q.is_running():live.append(p)
            except psutil.NoSuchProcess:pass
        m.save(Path(sys.argv[3])/'old-false-complete.json',dict(complete=rec['complete'],live=live))
        assert rec['complete'] and live


def run():
    W.mkdir(exist_ok=False)
    start=time.perf_counter();parent=time.process_time();results=[];cpu=0
    sha=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
    m.save(W/'source-bindings.json',dict(monitor=sha,synthetic=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),psutil=psutil.__version__,python=sys.version,base_executable=sys._base_executable,old_raw_SHA256=hashlib.sha256(Path('C:/Users/Admin/Desktop/Solar-simulator/scripts/qualification409/monitor200.py').read_bytes()).hexdigest()))
    cases=[('root0','quick',None,None),('joined','joined',None,None),('child','orphan',None,None),('grandchild','grandchild',None,None),('venv','orphan',None,None),('nonzero','nonzero',None,None),('crash','crash',None,None),('interrupt','burn','interrupt',None),('wall','sleep',None,('wall_seconds',.35)),('cpu','burn',None,('cpu_seconds',.15)),('memory','burn',None,('private_bytes',1024)),('disk','disk',None,('disk_bytes',1024)),('cleanup-race','orphan','race',None),('acquisition-race','joined','vanish',None),('identity-mismatch','burn','identity',None),('access-denied','burn','access',None),('receipt-write','quick','write',None),('short-parent','grandchild',None,None),('repeat-termination','burn','repeat',None),('old-false-complete','old',None,None)]
    for name,mode,fault,limit in cases:
        if cpu+time.process_time()-parent>45 or time.perf_counter()-start>130:raise RuntimeError('Synthetic allocation stop')
        case=W/name;case.mkdir();limits=dict(cpu_seconds=12,wall_seconds=10,private_bytes=512*1024**2,disk_bytes=16*1024**2)
        if limit:limits[limit[0]]=limit[1]
        cmd=[sys.executable,'-X','utf8','-B','-m',MODULE,'worker',mode,str(case)]
        hook=None;target=None;replacement=None
        if fault=='interrupt':
            def hook(s):raise KeyboardInterrupt('synthetic interrupt')
        if fault=='race':
            def hook(s):
                if s['worker_cpu']>.05:time.sleep(.12)
        if fault=='repeat':
            def hook(s):raise RuntimeError('cleanup requested; bounded repetition tested separately')
        if fault=='vanish':target='process_handle';replacement=lambda pid: (_ for _ in ()).throw(OSError(87,'synthetic vanished'))
        if fault=='identity':target='identity';replacement=lambda h: (_ for _ in ()).throw(RuntimeError('injected identity mismatch'))
        if fault=='access':target='process_handle';replacement=lambda pid: (_ for _ in ()).throw(PermissionError('synthetic AccessDenied'))
        if fault=='write':target='save';replacement=lambda *a: (_ for _ in ()).throw(OSError('injected receipt write failure'))
        error=None;rec=None
        try:
            if target:
                obj=m
                with patch.object(obj,target,replacement):rec=m.monitor(cmd,case/'guard',case,limits,hook=hook)
            else:rec=m.monitor(cmd,case/'guard',case,limits,hook=hook)
        except OSError as exc:error=str(exc)
        if rec:cpu+=rec['worker_CPU_seconds'] or 0
        success=name in ('root0','joined')
        reasons={'root0':None,'joined':None,'child':'unexpected-owned-descendant','grandchild':'unexpected-owned-descendant','venv':'unexpected-owned-descendant','nonzero':'root-nonzero','crash':'root-nonzero','interrupt':'interrupted','wall':'stage-wall','cpu':'stage-CPU','memory':'private-memory','disk':'stage-disk','cleanup-race':'unexpected-owned-descendant','acquisition-race':'monitor-error','identity-mismatch':'monitor-error','access-denied':'monitor-error','short-parent':'unexpected-owned-descendant','repeat-termination':'monitor-error','old-false-complete':'unexpected-owned-descendant'}
        ok=(rec is not None and rec['complete']==success and rec['limit_reason']==reasons[name] and rec['final_job']['active']==0) if fault!='write' else error is not None and not (case/'guard/supervisor.json').exists()
        liveness=[]
        for p in case.glob('*.pid.json'):
            q=json.loads(p.read_bytes());live=False
            try:live=psutil.Process(q['pid']).create_time()==q['creation_time'] and psutil.Process(q['pid']).is_running()
            except psutil.NoSuchProcess:pass
            liveness.append(dict(**q,alive=live));ok=ok and not live
        row=dict(name=name,expected_success=success,contract_check=ok,record=rec,error=error,process_identity_liveness=liveness,coverage='Actual native process scenario with explicit test hook where stated',fault=fault)
        results.append(row);m.save(case/'test-result.json',row)
        print(name,ok,rec and rec['limit_reason'],flush=True)
    m.save(W/'suite.json',dict(results=results,worker_CPU_seconds=cpu,parent_CPU_seconds=time.process_time()-parent,wall_seconds=time.perf_counter()-start,all_contract_checks=all(x['contract_check'] for x in results),scope='Probes, not complete qualification; missing negative controls listed in report'))


if __name__=='__main__':
    if sys.argv[1]=='worker':worker(sys.argv[2])
    elif sys.argv[1]=='run':run()
