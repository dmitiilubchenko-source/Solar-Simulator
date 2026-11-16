"""Separate409.5 operational budget, reviewed evidence and filtered project queue."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
R=Path(__file__).resolve().parents[2];A=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116');C=Path('C:/Users/Admin/Documents/Codex/Solar4095-backup-20261116')
BASE=Path('C:/Users/Admin/Documents/Codex/2026-10-29/files-pasted-by-the-user-codex/outputs');sys.path.insert(0,str(BASE));import backup,backup_core as core

def seal():
    C.mkdir(exist_ok=False)
    p=dict(stage='409.5_PORTABLE_BACKUP',hard=dict(cpu_seconds=240,wall_seconds=3600,private_bytes=1024**3,disk_bytes=512*1024**2),early=dict(cpu_seconds=192,wall_seconds=2880,private_bytes=900*1024**2,disk_bytes=450*1024**2),CPU_final_reserve=20,wall_final_reserve=180,per_object_wall=420,external_parts_reserve=128*1024**2,forecast=dict(review_prepare_CPU=20,transfer_supervision_CPU=85,assembly_CPU=10,finalization_CPU=20,active_wall=1800,disk=370000000),monitor_path='scripts/qualification409/monitor200.py',monitor_SHA256=core.sha(R/'scripts/qualification409/monitor200.py'),parent='1lMlX0WvaL3b14sU2UKMB_8DHobSofuYI',account='dmitiilubchenko@gmail.com',note='No409reuploads; bounded freshbytes only. Sampled notOSquota. Connectorwall separate, serviceCPU unavailable.')
    core.atomic_json(C/'plan.json',p);core.atomic_json(C/'initial-resources.json',dict(charged_CPU_seconds=5,charged_active_wall_seconds=10,kind='Conservativeinitialsetupallowance'))
    code=(R/'scripts/qualification409/backup_guard.py').read_text(encoding='utf8').replace('Solar409-backup-20261111','Solar4095-backup-20261116')
    code=code.replace("limits=dict(p['early']);", "limits=dict(p['early']);limits['disk_bytes']-=p['external_parts_reserve'];")
    (R/'scripts/qualification4095/backup_guard.py').write_text(code,encoding='utf8',newline='\n')
    worker=(R/'scripts/qualification409/read_object.py').read_text(encoding='utf8').replace('Solar409-20261111','Solar4095-backup-20261116')
    (C/'read_object.py').write_text(worker,encoding='utf8',newline='\n')
    print('Separate409.5 backup budget sealed; forecast135CPU1800wall370MB, hard unchanged')

def prepare():
    assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
    chosen=[];excluded=[]
    for f in A.rglob('*'):
        if not f.is_file():continue
        rel=f.relative_to(A);keep=False
        if len(rel.parts)==1:keep=f.suffix in {'.json','.py','.log'}
        if rel.parts[0].startswith('guard-'):keep=f.suffix in {'.json','.jsonl','.log'}
        if rel.parts[0] in {'failure-raw','initial-verification-assets'}:keep=f.suffix in {'.json','.txt','.py','.md','.cmd'}
        if keep:
            issue=core.review(f)
            if issue:raise ValueError('Evidence requires review: '+str(rel)+': '+issue)
            chosen.append((rel.as_posix(),f))
        else:excluded.append(dict(path=rel.as_posix(),size=f.stat().st_size,sha256=core.sha(f) if rel.parts[0]=='security-fixtures' or f.name=='hook-secret.txt' else None,reason='Recoverable package/runtime/duplicate fixture or synthetic secret/unsafe payload; original retained locally'))
    commit=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()
    manifest=dict(project='Solar-Simulator',stage='409.5',git_commit=commit,files=[dict(path=n,size=f.stat().st_size,sha256=core.sha(f)) for n,f in chosen],excluded=excluded)
    archive=C/'Solar-Simulator-4095-evidence-20261116.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for n,f in chosen:z.write(f,n)
        z.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
    assert core.review(archive) is None
    a=json.loads((A/'new-package.json').read_bytes());optin=json.loads((A/'backup-optin.json').read_bytes())
    assert core.sha(optin['reviewer'])==optin['reviewer_sha256'] and core.sha(optin['contract'])==optin['contract_sha256']
    with backup.lock():
        cfg=backup.read(BASE/'backup-config.json',{});p=next(x for x in cfg['projects'] if x['name']=='Solar-Simulator')
        assert p['cloud_folder_id']=='1lMlX0WvaL3b14sU2UKMB_8DHobSofuYI'
        p['filtered_prepare_files']=[a['archive'],str(archive)];p['portable_review4095']=optin
        p.setdefault('expected_sha256',{}).update({Path(a['archive']).name:a['archive_SHA256'],archive.name:core.sha(archive)})
        core.atomic_json(BASE/'backup-config.json',cfg)
    process=subprocess.run(['powershell','-NoProfile','-File',str(BASE/'run-backup.ps1'),'-Project','Solar-Simulator'],capture_output=True,timeout=180)
    (C/'prepare.log').write_bytes(process.stdout+process.stderr);assert process.returncode==0
    m=backup.read(backup.MANIFEST,{});parents=[x for x in m['files'] if x['project']=='Solar-Simulator' and x['source'] in {a['archive'],str(archive)}]
    assert len(parents)==2 and all(x['status'] in {'PENDING_UPLOAD','CHUNKED_TRANSPORT_PENDING'} for x in parents),[(x['name'],x['status'],x.get('reason')) for x in parents]
    parentsha={x['sha256'] for x in parents}
    queue=[x for x in m['files'] if x['project']=='Solar-Simulator' and (x.get('transport_parent_sha256') in parentsha or x['source']==str(archive) or x['name']==f'Solar-Simulator-recovery-{commit}.json')]
    core.atomic_json(C/'queue.json',dict(rows=queue,portable=parents[0] if parents[0]['source']==a['archive'] else parents[1]))
    print('Filtered queue prepared:',len(queue),'objects. Still CLOUD_UNVERIFIED before readback.')

if __name__=='__main__':
    if sys.argv[1:] == ['seal']:seal()
    elif sys.argv[1:] == ['prepare']:prepare()
    else:raise ValueError('Explicit seal/prepare required')
