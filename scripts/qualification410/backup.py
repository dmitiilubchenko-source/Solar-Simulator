"""Evidence-only backup410. No failed full410 monitor is treated as admitted."""
from pathlib import Path
import json,subprocess,sys,zipfile
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar410-20261116');C=Path('C:/Users/Admin/Documents/Codex/Solar410-backup-20261116');BASE=Path('C:/Users/Admin/Documents/Codex/2026-10-29/files-pasted-by-the-user-codex/outputs')
sys.path.insert(0,str(BASE));import backup as mechanism,backup_core as core

def seal():
 C.mkdir(exist_ok=False)
 core.atomic_json(C/'plan.json',dict(kind='410-small-evidence-backup-only',hard=dict(cpu_seconds=60,wall_seconds=300,private_bytes=512*1024**2,disk_bytes=64*1024**2),scope='Bounded metadata/fs operations and direct-base-Python -I -S leaf download workers only. Not admission of frozen monitor for full410. Counts remain within unused original410 budget.',CPU_final_reserve=10,wall_final_reserve=20))
 core.atomic_json(C/'initial-resources.json',dict(charged_CPU_seconds=5,charged_active_wall_seconds=10,kind='Conservative archive/queue/Git operations allowance'))
 worker=(R/'scripts/qualification409/read_object.py').read_text(encoding='utf8').replace('Solar409-20261111','Solar410-backup-20261116');(C/'read_object.py').write_text(worker,encoding='utf8',newline='\n')
 print('Evidence backup scoped60CPU300wall512MiB64MiB, no new scientific work')

def prepare():
 assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
 chosen=[p for p in W.rglob('*') if p.is_file() and p.suffix in {'.json','.py','.log','.txt'}]
 assert sum(p.stat().st_size for p in chosen)<4*1024**2
 for p in chosen:assert core.review(p) is None,str(p)
 archive=C/'Solar-Simulator-410-admission-20261116.zip'
 manifest=dict(project='Solar-Simulator',scope='Failed monitor admission only; no full410 or scientific orbits',git_commit=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),files=[dict(path=p.relative_to(W).as_posix(),size=p.stat().st_size,sha256=core.sha(p)) for p in chosen],restore='Clone the exact published dev commit. Restore raw evidence separately. Original33114f5a portable is already cloudverified409.5; do not reupload or run full410 until separate monitor correction/admission.')
 with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
  for p in chosen:z.write(p,p.relative_to(W).as_posix())
  z.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
 assert core.review(archive) is None
 with mechanism.lock():
  cfg=mechanism.read(BASE/'backup-config.json',{});p=next(x for x in cfg['projects'] if x['name']=='Solar-Simulator');assert p['cloud_folder_id']=='1lMlX0WvaL3b14sU2UKMB_8DHobSofuYI';p['filtered_prepare_files']=[str(archive)];p.setdefault('expected_sha256',{})[archive.name]=core.sha(archive);core.atomic_json(BASE/'backup-config.json',cfg)
 result=subprocess.run(['powershell','-NoProfile','-File',str(BASE/'run-backup.ps1'),'-Project','Solar-Simulator'],capture_output=True,timeout=60);(C/'prepare.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
 commit=manifest['git_commit'];m=mechanism.read(mechanism.MANIFEST,{});rows=[x for x in m['files'] if x['project']=='Solar-Simulator' and (x['source']==str(archive) or x['name']==f'Solar-Simulator-recovery-{commit}.json')];assert len(rows)==2 and all(x['status']=='PENDING_UPLOAD' for x in rows)
 core.atomic_json(C/'queue.json',rows);print(json.dumps([{k:x.get(k) for k in ['name','source','size','sha256','status']} for x in rows]))

if __name__=='__main__':
 if sys.argv[1:] == ['seal']:seal()
 elif sys.argv[1:] == ['prepare']:prepare()
 else:raise ValueError('Explicit seal/prepare required')
