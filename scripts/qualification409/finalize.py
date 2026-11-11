"""Bounded offline final identity/accounting supplement; no integrations or rebuilds."""
from pathlib import Path
import ast, hashlib, json, subprocess

R=Path(__file__).resolve().parents[2]
W=Path('C:/Users/Admin/Documents/Codex/Solar409-build-20261111')
S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v')
p=json.loads((W/'plan.json').read_bytes())
pre=json.loads((W/'build-preflight.json').read_bytes())
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'])
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==p['base_runtime_commit']
assert all(sha(S/n)==v and sha(Path(p['packaging_root'])/n)==v for n,v in pre['runtime_files'].items())
assert sha(p['wheel'])==p['wheel_SHA256']
from solar_simulator.recipe import runtime_fingerprint
assert hashlib.sha256((json.dumps(runtime_fingerprint('rust'),indent=2)+'\n').encode()).hexdigest()==p['source_fingerprint']
for f in (R/'scripts/qualification409').glob('*.py'):ast.parse(f.read_bytes(),filename=str(f))
for f in (R/'scripts/qualification409').glob('*.json'):json.loads(f.read_bytes())
rows=[json.loads(f.read_bytes()) for f in W.glob('*-resources.json')]
resource=dict(charged_CPU=sum(x['charged_CPU_seconds'] for x in rows)+20,
              charged_active_wall=sum(x['charged_active_wall_seconds'] for x in rows)+40,
              finalization_allowance_CPU=20,finalization_allowance_wall=40,
              private_sampled_peak=max(x.get('record',{}).get('peak_private_tree_sampled',0) for x in rows),
              bytes_in_W=sum(f.stat().st_size for f in W.rglob('*') if f.is_file()),
              external_data_allowance=p['external_source_reserve'],
              initial_and_final_allowances='Conservative charges, not measured consumption',
              measurement_limits='Sampled process discovery/private peaks; not OSquota. Supervisor and failed attempts charged.')
assert resource['charged_CPU']<p['early']['cpu_seconds'] and resource['charged_active_wall']<p['early']['wall_seconds']
assert resource['bytes_in_W']+resource['external_data_allowance']<p['early']['disk_bytes']
out=dict(stage=409,source_identity='PASS_EXACT_RAW_BYTES',resource_build=resource,
         cloud408='VERIFIED_NEW_INDEPENDENT_READBACK',portable_build='PASS',
         acceptance410='BLOCKED_STOCK_FRESH_YEAR_SOURCE_GATE_NOT_RUN',release='NO-GO',
         no_native_rebuild=True,original_scientific_receipts_unchanged=True)
dest=R/'scripts/qualification409/final-closure.json'
with dest.open('x',encoding='utf8',newline='\n') as f:json.dump(out,f,indent=2);f.write('\n')
report=R/'docs/portable-build-409.json';data=json.loads(report.read_bytes());data['resource_build_final']=resource
report.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
with (R/'docs/portable-build-409.md').open('a',encoding='utf8',newline='\n') as f:
 f.write(f"\nФинальный учёт409B: {resource['charged_CPU']:.6f}CPU / {resource['charged_active_wall']:.6f}activewall\nвключая отдельный консервативный хвост20CPU/40wall; все ранние границы соблюдены.\nПодробности и ограничения измерения — [final closure](../scripts/qualification409/final-closure.json).\n")
print(json.dumps(out))
