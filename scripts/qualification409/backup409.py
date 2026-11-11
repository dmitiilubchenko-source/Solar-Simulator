"""Reviewed409 evidence archive and filtered Project-Archives preparation only."""
from pathlib import Path
import hashlib, importlib.util, json, subprocess, sys, zipfile

R=Path(__file__).resolve().parents[2]
C=Path('C:/Users/Admin/Documents/Codex/Solar409-backup-20261111')
BASE=Path('C:/Users/Admin/Documents/Codex/2026-10-29/files-pasted-by-the-user-codex/outputs')
sys.path.insert(0,str(BASE));import backup,backup_core as core

def seal():
 C.mkdir(exist_ok=False)
 plan=dict(stage='409C_NEW_BACKUP_ONLY',hard=dict(cpu_seconds=240,wall_seconds=3600,private_bytes=1024**3,disk_bytes=512*1024**2),
           early=dict(cpu_seconds=192,wall_seconds=2880,private_bytes=900*1024**2,disk_bytes=450*1024**2),
           CPU_final_reserve=20,wall_final_reserve=180,per_object_wall=420,
           forecast=dict(CPU=130,active_wall=2200,new_bytes=370000000),
           monitor_path='scripts/qualification409/monitor200.py',
           monitor_SHA256=core.sha(R/'scripts/qualification409/monitor200.py'),
           account='dmitiilubchenko@gmail.com',parent='1lMlX0WvaL3b14sU2UKMB_8DHobSofuYI',
           scope='New409evidence and exactportable only; no408reupload. Connector wall charged separately; remote-service CPU not locally measurable.',
           limitation='200ms sampled supervision; independent download required. CLOUD_UNVERIFIED on missing proof.')
 core.atomic_json(C/'plan.json',plan)
 core.atomic_json(C/'initial-resources.json',dict(charged_CPU_seconds=5,charged_active_wall_seconds=10,kind='Conservativeinitialallowance; notmeasured'))
 print('409C plan sealed; prepare must run under backup_guard')

def prepare():
 plan=json.loads((C/'plan.json').read_bytes())
 # Only bounded evidence files, never recursive build outputs/dependencies/envs.
 selected=[]
 for label,rootname in [('A','Solar409-20261111'),('B','Solar409-build-20261111')]:
  root=C.parent/rootname
  for f in root.rglob('*'):
   if not f.is_file():continue
   rel=f.relative_to(root)
   keep=(len(rel.parts)==1 and f.suffix in {'.json','.log','.py','.md','.txt'})
   keep|=(rel.parts[0].startswith('guard-') and f.suffix in {'.json','.log','.jsonl'})
   keep|=(rel.parts[0]=='faults' and f.suffix in {'.json','.log','.jsonl'})
   keep|=(rel.parts[0]=='downloads' and f.name.endswith('-completion.json'))
   keep|=(rel.as_posix()=='historical-export/VERIFICATION-SOURCE.json')
   if not keep:continue
   assert not f.is_symlink() and f.name not in core.PRIVATE_CONTEXT_NAMES
   issue=core.review(f)
   if issue:raise ValueError(f'Evidence requires review: {rel}: {issue}')
   selected.append((label+'/'+rel.as_posix(),f))
 commit=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()
 assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
 manifest=dict(project='Solar-Simulator',stage=409,git_commit=commit,
  role='Compact evidence, NOT portableZIP; excludes already verified408binary payloads and recoverabledependencies/sourcecopies',
  files=[dict(name=n,source=str(f),size=f.stat().st_size,sha256=core.sha(f)) for n,f in selected])
 archive=C/'Solar-Simulator-stage409-evidence-20261111.zip'
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=4) as z:
  for n,f in selected:z.write(f,n)
  z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for row in manifest['files']:
   b=z.read(row['name']);assert len(b)==row['size'] and hashlib.sha256(b).hexdigest()==row['sha256']
 assert core.review(archive) is None
 report=json.loads((R/'docs/portable-build-409.json').read_bytes());portable=Path(report['archive'])
 assert core.sha(portable)==report['archive_SHA256'] and portable.stat().st_size==report['archive_size']
 issue=core.review(portable)
 if issue:raise ValueError('Portable archive review: '+issue)
 # No concurrent prepare/config/manifest mutations; exclusive existing mechanism lock.
 with backup.lock():
  cfg=backup.read(BASE/'backup-config.json',{})
  core.atomic_json(C/'config-before.json',cfg)
  row=next(x for x in cfg['projects'] if x['name']=='Solar-Simulator')
  assert row['cloud_folder_id']==plan['parent']
  row['filtered_prepare_files']=[str(archive),str(portable)]
  core.atomic_json(BASE/'backup-config.json',cfg)
 run=subprocess.run(['powershell','-NoProfile','-File',str(BASE/'run-backup.ps1'),'-Project','Solar-Simulator'],capture_output=True,timeout=90)
 (C/'prepare.log').write_bytes(run.stdout+run.stderr);assert run.returncode==0
 m=backup.read(BASE/'backup-manifest.json',{})
 wanted={str(archive),str(portable)}
 parents=[x for x in m['files'] if x['project']=='Solar-Simulator' and x['source'] in wanted]
 assert len(parents)==2 and all(x['status'] in {'PENDING_UPLOAD','CHUNKED_TRANSPORT_PENDING'} for x in parents)
 hashes={x['sha256'] for x in parents}
 rows=[x for x in m['files'] if x['project']=='Solar-Simulator' and (x.get('transport_parent_sha256') in hashes or x['source'] in wanted or x['name']==f'Solar-Simulator-recovery-{commit}.json')]
 core.atomic_json(C/'queue.json',dict(git_commit=commit,rows=rows))
 print(json.dumps(dict(evidence=str(archive),size=archive.stat().st_size,sha256=core.sha(archive),files=len(selected),queue=len(rows))))

if __name__=='__main__':
 if sys.argv[1:] == ['seal']:seal()
 elif sys.argv[1:] == ['prepare']:prepare()
 else:raise ValueError('Explicit seal or prepare required; never rerun completed steps')
