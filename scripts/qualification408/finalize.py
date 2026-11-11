"""Final408 append-only closure; no self-receipt cycle or candidate edits."""
from pathlib import Path
import ast,hashlib,json,subprocess,sys,time
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar408-20261111');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
resources=[];phase_rows=[]
for launch in sorted(W.glob('launch-*.json')):
    name=launch.stem.removeprefix('launch-');f=W/(name+'-resources.json');r=json.loads(f.read_bytes());supervisor=W/('guard-'+name)/'supervisor.json';raw=json.loads(supervisor.read_bytes());assert r['record']==raw and raw['limit_reason'] is None
    expected_exit=1 if name=='report' else 0;assert raw['exit_code']==expected_exit
    phase_rows.append(dict(name=name,exit_code=expected_exit,classification='Preserved reporting-only self-receipt FileNotFoundError' if name=='report' else 'Completed phase',resource_SHA256=sha(f),supervisor_SHA256=sha(supervisor),launch_SHA256=sha(launch)));resources.append(r)
allowance=dict(charged_CPU_seconds=20,charged_active_wall_seconds=45,kind='Predeclared finalization20CPU45wall upper charge, not measurement: compact audits/Git/privatecontext; backup operational budget separate')
with (W/'finalization-resources.json').open('x') as f:json.dump(allowance,f)
resources.append(allowance);initial=json.loads((W/'initial-resources.json').read_bytes());resources.append(initial)
cpu=sum(x['charged_CPU_seconds'] for x in resources);wall=sum(x['charged_active_wall_seconds'] for x in resources);assert cpu<1920 and wall<2160
r=json.loads((R/'docs/release-source-acceptance-408.json').read_bytes());r['resources'].update(charged_CPU_seconds=cpu,charged_active_wall_seconds=wall,finalization_allowance=allowance,limitations='Exact38550msrequested monitor; memory/tree peaks sampled, not OSquota. Worker/supervisor charged; initial10CPU25wall and finalization20CPU45wall conservative allowances, not measured. Includes failed report helper; backup separate.')
r['resources']['W_disk_bytes']=sum(p.stat().st_size for p in W.rglob('*') if p.is_file())
a=json.loads((W/'independent-audit.json').read_bytes());assert a['technical_GO'] and a['nodes_checked']==3083
closure=dict(stage=408,candidate=r['candidate'],tree=r['tree'],plan_SHA256=sha(W/'plan.json'),evidence_manifest_SHA256=sha(W/'evidence-manifest.json'),audit_SHA256=sha(W/'independent-audit.json'),all_launches_reconciled=phase_rows,resource_totals=r['resources'],primary_acceptance_failures=0,reporting_only_failed_attempts=1,decision=r['decision'],not_release_approval=True,executor_source_SHA256={str(p.relative_to(R)):sha(p) for p in (R/'scripts/qualification408').glob('*.py')})
(W/'final-closure.json').write_text(json.dumps(closure,indent=2)+'\n',encoding='utf8',newline='\n');(R/'scripts/qualification408/final-closure.json').write_bytes((W/'final-closure.json').read_bytes());r['final_closure_SHA256']=sha(W/'final-closure.json');r['resources']['auditor_own_receipt_reconciled']=True
(R/'docs/release-source-acceptance-408.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
with (R/'docs/release-source-acceptance-408.md').open('ab') as f:f.write((f'\nFinal closure: {cpu:.6f}chargedCPU/{wall:.6f}activewall; включает finalization allowance20CPU/45wall (не измерение). Все supervisor/completion receipts закрыты, в том числе сохранённый report-only exit1 и исправленный report2exit0. [Полная closure](../scripts/qualification408/final-closure.json). Primary tests/runtime failures0.\n').encode())
for p in (R/'scripts/qualification408').glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
for p in [R/'docs/release-source-acceptance-408.json',*(R/'scripts/qualification408').glob('*.json')]:json.loads(p.read_bytes())
subprocess.run([sys.executable,'-X','utf8','-B','scripts/project_inventory.py','--write'],cwd=R,check=True)
