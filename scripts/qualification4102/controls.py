"""Targeted ownership/receipt controls, independently held foreign process."""
from pathlib import Path
import copy,json,os,subprocess,sys,time,msvcrt
from unittest.mock import patch
from . import monitor as m
from .run import valid,PROBE
W=Path('C:/Users/Admin/Documents/Codex/Solar4102-20261118/controls2')


def run():
    W.mkdir();start=time.perf_counter();cpu=time.process_time();rows=[]
    limits=dict(cpu_seconds=10,wall_seconds=8,private_bytes=512*1024**2,disk_bytes=8*1024**2)
    outsider=subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(8)'])
    try:
        with (W/'foreign-handle.txt').open('xb') as f:
            h=msvcrt.get_osfhandle(f.fileno());os.set_handle_inheritable(h,True)
            rec=m.monitor([sys.executable,'-I','-B',str(PROBE),'handle',str(W),str(h)],W/'handle',W,limits)
            rows.append(dict(name='foreign-handle',ok=rec['complete'] and 'foreign-handle-valid False' in (W/'handle/stdout.log').read_text(),record=rec))
        original=m.process_handle
        with patch.object(m,'process_handle',lambda pid:original(outsider.pid)):
            rec=m.monitor([sys.executable,'-I','-B',str(PROBE),'burn',str(W)],W/'identity',W,limits)
        rows.append(dict(name='foreign-identity',ok=not rec['complete'] and any('no longer belongs' in e['message'] for e in rec['error']) and outsider.poll() is None,record=rec,scope='Real IsProcessInJob false path using held foreign process; simulated PID substitution, not real OS PID reuse'))
        job=m.checked(m.create_job(None,None))
        try:m.checked(m.terminate_job(job,1));m.checked(m.terminate_job(job,1));rows.append(dict(name='repeated-termination-empty-job',ok=m.accounting(job)['active']==0))
        finally:m.close(job)
        source=json.loads((W/'handle/supervisor.json').read_bytes());sha=source['monitor_SHA256']
        for name in ['missing','invalid','noCPU','wrongSHA']:
            p=W/(name+'.json')
            if name=='invalid':p.write_text('broken')
            elif name!='missing':
                value=copy.deepcopy(source)
                if name=='noCPU':value['worker_CPU_seconds']=None
                if name=='wrongSHA':value['monitor_SHA256']='0'*64
                p.write_text(json.dumps(value))
            try:valid(p,sha);ok=False
            except (ValueError,FileNotFoundError):ok=True
            rows.append(dict(name='consumer-'+name,ok=ok,scope='New explicit receipt reader only; existing acceptance consumers unchanged'))
        lossdir=W/'loss';lossdir.mkdir()
        root=subprocess.Popen([sys.executable,'-B','-m','scripts.qualification4102.controls','loss',str(lossdir)])
        root.wait(timeout=8)
        identities=json.loads((lossdir/'identities.json').read_bytes());gone=[]
        for pid,birth in identities:
            try:
                h=m.process_handle(pid)
                try:gone.append(m.identity(h)[0]!=birth or m.wait(h,3000)==0)
                finally:m.close(h)
            except OSError as exc:gone.append(getattr(exc,'winerror',None)==87)
        rows.append(dict(name='supervisor-loss',ok=root.returncode==23 and bool(gone) and all(gone) and not (lossdir/'guard/supervisor.json').exists(),root_exit=root.returncode,identities=identities,confirmed_gone=gone))
        rows.append(dict(name='unrelated-process-survival',ok=outsider.poll() is None,pid=outsider.pid))
    finally:
        if outsider.poll() is None:outsider.terminate()
        outsider.wait(timeout=3)
    m.save(W/'results.json',dict(rows=rows,parent_CPU=time.process_time()-cpu,wall=time.perf_counter()-start,foreign_root_exit=outsider.returncode))
    print(json.dumps([(r['name'],r['ok']) for r in rows]))


def loss(out):
    n=0
    def hook(s):
        nonlocal n
        n+=1
        if n<3:return
        pids=m.psutil.Process().children(recursive=True);items=[]
        for p in pids:
            try:
                h=m.process_handle(p.pid)
                try:items.append([p.pid,m.identity(h)[0]])
                finally:m.close(h)
            except OSError:pass
        m.save(out/'identities.json',items);os._exit(23)
    m.monitor([sys.executable,'-I','-B',str(PROBE),'burn',str(out)],out/'guard',out,dict(cpu_seconds=5,wall_seconds=5,private_bytes=512*1024**2,disk_bytes=4*1024**2),hook=hook)


if __name__=='__main__':
    if sys.argv[1:] and sys.argv[1]=='loss':loss(Path(sys.argv[2]))
    else:run()
