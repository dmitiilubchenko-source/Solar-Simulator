"""Independent cloud bytes, exact part ordering, member hashes and manifest rollup."""
from pathlib import Path
import hashlib,json,shutil,sys,zipfile
R=Path(__file__).resolve().parents[2];A=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116');C=Path('C:/Users/Admin/Documents/Codex/Solar4095-backup-20261116')
BASE=Path('C:/Users/Admin/Documents/Codex/2026-10-29/files-pasted-by-the-user-codex/outputs');sys.path.insert(0,str(BASE));import backup,backup_core as core
metadata=json.loads((C/'cloud-metadata.json').read_bytes());transport=json.loads((C/'downloads/manifest.bin').read_bytes());audit=json.loads((A/'new-package.json').read_bytes())
assert transport['sha256']==audit['archive_SHA256'] and transport['size']==audit['archive_size']
for d in metadata:
    label='part%02d'%(d['i']+1) if d['i']<7 else ['manifest','evidence','recipe'][d['i']-7]
    receipt=json.loads((C/'downloads'/(label+'-completion.json')).read_bytes());row=d['row'];path=C/'downloads'/(label+'.bin')
    assert receipt['status']=='VERIFIED_SHA256_SIZE' and receipt['id']==d['id']
    assert core.sha(path)==row['sha256'] and path.stat().st_size==row['size']
    m=d['metadata'];assert m['parent_ids']==['1lMlX0WvaL3b14sU2UKMB_8DHobSofuYI'] and int(m['size'])==row['size']
    assert len(m['permissions'])==1 and m['permissions'][0]['role']=='owner' and m['permissions'][0]['emailAddress']=='dmitiilubchenko@gmail.com'
out=C/'cloud-reassembled.zip'
with out.open('xb') as f:
    for i,part in enumerate(transport['parts']):
        path=C/'downloads'/('part%02d.bin'%(i+1));row=metadata[i]['row']
        assert (part['name'],part['size'],part['sha256'])==(row['name'],row['size'],row['sha256'])
        with path.open('rb') as src:shutil.copyfileobj(src,f,1024*1024)
assert core.sha(out)==audit['archive_SHA256'] and out.stat().st_size==audit['archive_size']
contract=json.loads((A/'asset-contract.json').read_bytes());members=[]
assert core.sha(A/'asset-contract.json')==audit['asset_contract_SHA256']
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None and len(z.namelist())==6005
    for i in z.infolist():
        n='/'.join(Path(i.filename).parts[1:]);b=z.read(i);expected=contract['files'][n]
        assert len(b)==expected['size'] and hashlib.sha256(b).hexdigest()==expected['sha256'] and f'{i.CRC:08x}'==expected['CRC32']
        members.append(n)
assert set(members)==set(contract['files'])
with zipfile.ZipFile(C/'downloads/evidence.bin') as z:
    assert z.testzip() is None;m=json.loads(z.read('MANIFEST.json'))
    assert set(z.namelist())=={x['path'] for x in m['files']}|{'MANIFEST.json'}
    for row in m['files']:
        b=z.read(row['path']);assert len(b)==row['size'] and hashlib.sha256(b).hexdigest()==row['sha256']
    evidence_count=len(z.namelist())
recipe=json.loads((C/'downloads/recipe.bin').read_bytes());assert recipe['git_commit']=='aaa8d4dd9a8aad268917c2311a30ddb543df8544' and recipe['publication_proof']
with backup.lock():
    m=backup.read(backup.MANIFEST,{})
    for d in metadata:
        row=next(x for x in m['files'] if x['project']=='Solar-Simulator' and x['source']==d['row']['source'] and x['sha256']==d['row']['sha256'])
        row.update(status='CLOUD_VERIFIED_SHA256',cloud_location='https://drive.google.com/file/d/'+d['id']+'/view',cloud_metadata=d['metadata'],cloud_evidence=dict(file_id=d['id'],sha256=row['sha256'],size=row['size'],parent_id='1lMlX0WvaL3b14sU2UKMB_8DHobSofuYI',verified_at=core.now(),method='Independent freshconnector HTTPS bytes; local readback SHA/size'))
        backup.write_record(m,row)
    backup.refresh_chunks(m)
    parent=next(x for x in m['files'] if x['project']=='Solar-Simulator' and x['sha256']==audit['archive_SHA256'] and 'transport' in x)
    assert parent['status']=='CLOUD_VERIFIED_CHUNKS_SHA256'
    parent['review_contract']=dict(sha256=audit['asset_contract_SHA256'],reviewer_SHA256=core.sha(R/'scripts/qualification4095/portable_review.py'));backup.write_record(m,parent)
result=dict(stage='409.5',status='CLOUD_PORTABLE_VERIFIED',archive_SHA256=audit['archive_SHA256'],archive_size=audit['archive_size'],member_count=6005,evidence_member_count=evidence_count,part_count=7,objects=metadata,transport=transport,account='dmitiilubchenko@gmail.com',parent='1lMlX0WvaL3b14sU2UKMB_8DHobSofuYI',owner_only=True,CRC_SHA_all_members=True,original409_not_uploaded=True,no_full410=True)
core.atomic_json(C/'cloud-verification.json',result)
print('CLOUD_PORTABLE_VERIFIED: full ZIP +6005CRC/SHA; evidence and recipe independent bytes verified')
