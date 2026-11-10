"""Bounded scanner comparison and genuine resource/termination fault controls."""
import ast,hashlib,importlib.util,json,os,sys,time
from pathlib import Path
import psutil
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar407-20261110');run_label=sys.argv[1] if len(sys.argv)>1 else 'prototype';D=W/('monitor-tests-'+run_label);D.mkdir()
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
oldpath=R/'.tools/qualification385/offline_monitor.py';newpath=R/'scripts/qualification407/monitor_prototype.py'
old=load('oldmon407',oldpath);new=old if run_label=='retained' else load('newmon407',newpath)
a,b=map(lambda p:ast.parse(p.read_text()),(oldpath,newpath))
for tree in (a,b):
    tree.body=[n for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name!='disk_size']
assert ast.dump(a)==ast.dump(b),'Only disk traversal may differ'
static=D/'static';static.mkdir()
for j in range(20):
    folder=static/str(j);folder.mkdir()
    for i in range(100):(folder/str(i)).write_bytes(bytes(i%17))
timings=[]
for root in (static,W/'env'):
    row=dict(root=str(root))
    for label,m in (('old',old),('new',new)):
        start=time.process_time();wall=time.perf_counter();sizes=[m.disk_size(root) for _ in range(4)]
        row[label]=dict(CPU=time.process_time()-start,wall=time.perf_counter()-wall,sizes=sizes)
    assert row['old']['sizes']==row['new']['sizes'];timings.append(row)
(static/'new').write_bytes(bytes(12345));assert old.disk_size(static)==new.disk_size(static)
results={}
for kind in ('CPU','wall','RAM','disk','interrupt','termination','prior-budget'):
    stage=D/kind;stage.mkdir()
    limits=dict(cpu_seconds=10,wall_seconds=3,private_bytes=512*1024**2,disk_bytes=8*1024**2)
    code='import time;time.sleep(2)';used=0.;hook=None
    if kind=='CPU':limits['cpu_seconds']=.15;code='while True: pass'
    elif kind=='wall':limits['wall_seconds']=.15
    elif kind=='RAM':limits['private_bytes']=64*1024**2;code='import time;x=bytearray(128*1024**2);time.sleep(2)'
    elif kind=='disk':
        limits['disk_bytes']=512*1024;code=f'from pathlib import Path;import time;Path({str(stage/"data.bin")!r}).write_bytes(bytes(1024**2));time.sleep(2)'
    elif kind=='prior-budget':limits['cpu_seconds']=1;used=1.1
    else:
        code=f'''import subprocess,sys,time,json
from pathlib import Path
p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
Path({str(stage/'checkpoint.json')!r}).write_text(json.dumps(dict(child=p.pid,committed=True)))
time.sleep(30)'''
        if kind=='termination':limits['wall_seconds']=.35
        else:
            def hook(sample):
                if (stage/'checkpoint.json').exists():raise KeyboardInterrupt('fault407')
    result=new.monitor([sys.executable,'-X','utf8','-B','-c',code],stage/'supervisor',stage,limits,used_cpu=used,hook=hook)
    expected={'CPU':'stage-CPU','wall':'stage-wall','RAM':'private-memory','disk':'stage-disk','interrupt':'interrupted','termination':'stage-wall','prior-budget':'stage-CPU'}[kind]
    assert result['limit_reason']==expected and not result['complete'],(kind,result)
    assert (stage/'supervisor/supervisor.json').is_file()
    if kind in ('interrupt','termination'):
        cp=json.loads((stage/'checkpoint.json').read_bytes());assert cp['committed'] and not psutil.pid_exists(cp['child'])
    results[kind]=result
assert new.exceeded(dict(private_tree=0,disk=0,parent_cpu=.2,worker_cpu=.2),dict(private_bytes=10,disk_bytes=10,wall_seconds=10,cpu_seconds=1),.7,0)=='stage-CPU'
receipt=D/'exclusive.json';new.save(receipt,dict(cost=3))
try:new.save(receipt,dict(cost=0))
except FileExistsError:pass
else:raise AssertionError('Completed receipt overwritten')
# A partial/missing record is not valid JSON and is never promoted to complete.
partial=D/'partial.json.partial';partial.write_text('{"complete":')
try:json.loads(partial.read_bytes())
except ValueError:pass
else:raise AssertionError('Partial receipt accepted')
report=dict(status='PASS',only_disk_traversal_AST_changed=True,poll_seconds=.05,comparisons=timings,faults=results,partial_and_overwrite_rejected=True,limitations='Sampled guard, no OS quota; unchanged process-tree discovery/memory cadence/retained final CPU handles/tail policy. Same exact per-scan byte count with faster Windows DirEntry metadata traversal.')
new.save(W/('monitor-validation-'+run_label+'.json'),report);print(json.dumps(dict(status='PASS',timings=timings,faults=list(results))),flush=True)
