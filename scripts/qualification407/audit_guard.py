"""Exercise actual stage preflight AST against hostile resume records."""
import ast,json,time
from pathlib import Path
import psutil
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar407-20261110');D=W/'guard-negative';D.mkdir()
source=R/'scripts/qualification407/guard.py';tree=ast.parse(source.read_text())
start=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For))
stop=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assert))
code=compile(ast.Module(body=tree.body[start:stop+1],type_ignores=[]),str(source),'exec')
plan=json.loads((W/'plan.json').read_bytes())
def check(root,forecast=(1.,1.)):
    ns=dict(W=root,p=plan,forecast=forecast,json=json)
    exec(code,ns);return ns['cpu'],ns['wall']
def write(root,cpu,wall):
    (root/'phase-resources.json').write_text(json.dumps(dict(charged_CPU_seconds=cpu,charged_active_wall_seconds=wall,record=dict(complete=False))))
base=D/'resume';base.mkdir();write(base,120,30)
assert check(base)==check(base)==(120,30)  # Failed work charged on every resume.
(base/'launch-missing.json').write_text('{}')
try:check(base)
except RuntimeError:pass
else:raise AssertionError('Missing resource record accepted')
(base/'launch-missing.json').rename(base/'missing-evidence.txt')
(base/'partial-resources.json').write_text('{"charged_CPU_seconds":')
try:check(base)
except ValueError:pass
else:raise AssertionError('Partial record accepted')
(base/'partial-resources.json').rename(base/'partial-evidence.txt')
for cpu,wall in ((719.5,30),(120,959.5)):
    write(base,cpu,wall)
    try:check(base)
    except AssertionError:pass
    else:raise AssertionError('Prior resource budget reset or expanded')
process=psutil.Process();timing={}
for label,operation in [('tree_discovery',lambda:process.children(recursive=True)),('memory',lambda:process.memory_info()),('CPU',lambda:process.cpu_times())]:
    cpu=time.process_time();wall=time.perf_counter()
    for _ in range(100):operation()
    timing[label]=dict(calls=100,CPU=time.process_time()-cpu,wall=time.perf_counter()-wall)
old=json.loads((R/'.tools/acceptance406-20261109/full_stock_check-resources.json').read_bytes())['record']
result=dict(status='PASS_PREFLIGHT_NEGATIVE_CONTROLS',executed_actual_preflight_AST=True,failed_work_counted=True,missing_partial_rejected=True,resume_caps_unchanged=True,operation_microprofile=timing,old406=dict(samples=old['samples'],wall=old['wall_seconds'],supervisorCPU=old['parent_supervision_CPU_seconds'],workerCPU=old['worker_CPU_seconds'],mean_sample_cycle_seconds=old['wall_seconds']/old['samples']),prototype='NO-GO Windows transient-directory race; original385monitor retained, no old receipts rewritten',limitations='Microprofile one owned process; no extrapolation to fullpytest from static scans. Final Windows CPU handles and tail policy unchanged. Sparse sampling is not an OS quota.')
with (W/'guard-audit.json').open('x') as f:json.dump(result,f,indent=2)
print('PASS actual-stage preflight missing/partial/priorCPU/priorwall/resume controls; operation timing saved',flush=True)
