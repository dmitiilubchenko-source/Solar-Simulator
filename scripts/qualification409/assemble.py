"""Independent assembly/CRC/SHA of409A cloud bytes, never local408parts."""
import hashlib,json,os,time,zipfile
from pathlib import Path,PurePosixPath,PureWindowsPath
W=Path('C:/Users/Admin/Documents/Codex/Solar409-20261111');P=json.loads((W/'cloud-plan.json').read_bytes());start=time.time();out=W/'assembled';out.mkdir(exist_ok=False);parts=[]
for index,label in [(0,'part1'),(1,'part2'),(2,'part3'),(3,'manifest'),(4,'recipe')]:
    expected=P['files'][index];file=W/'downloads'/(label+'.bin');completion=json.loads((W/'downloads'/(label+'-completion.json')).read_bytes());assert completion['id']==expected['id'] and completion['status']=='VERIFIED_SHA256_SIZE';assert file.stat().st_size==expected['size']
    with file.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    assert digest==expected['sha256'];parts.append(dict(id=expected['id'],name=expected['name'],size=file.stat().st_size,SHA256=digest,label=label))
manifest=json.loads((W/'downloads/manifest.bin').read_bytes());assert manifest['size']==P['archive_size'] and manifest['sha256']==P['archive_SHA256'];assert manifest['parts']==[{k:x[k] for k in ['name','size','sha256']} for x in P['files'][:3]]
archive=out/'Solar-Simulator-stage408-20261111.zip';h=hashlib.sha256();total=0
with archive.open('xb') as f:
    for label in ['part1','part2','part3']:
        with (W/'downloads'/(label+'.bin')).open('rb') as stream:
            for b in iter(lambda:stream.read(1024**2),b''):h.update(b);total+=len(b);f.write(b)
    f.flush();os.fsync(f.fileno())
assert total==P['archive_size'] and h.hexdigest()==P['archive_SHA256']
with zipfile.ZipFile(archive) as z:
    assert len(z.namelist())==1110 and len(set(z.namelist()))==1110;assert z.testzip() is None
    payload=json.loads(z.read('BACKUP-PAYLOAD-MANIFEST.json'));assert payload['format']=='deduplicated-v2' and len(payload['files'])==2982;checked={}
    for row in payload['files']:
        name=row['path'];posix=PurePosixPath(name);win=PureWindowsPath(name);assert not posix.is_absolute() and not win.drive and '..' not in posix.parts
        member='blobs/'+row['sha256']
        if member in checked:
            assert checked[member]==row['size'];continue
        digest=hashlib.sha256();size=0
        with z.open(member) as stream:
            for b in iter(lambda:stream.read(1024**2),b''):digest.update(b);size+=len(b)
        assert size==row['size'] and digest.hexdigest()==row['sha256'];checked[member]=size
    assert len(checked)==1109 and set(z.namelist())==set(checked)|{'BACKUP-PAYLOAD-MANIFEST.json'}
record=dict(status='CLOUD408_VERIFIED_SHA256_SIZE_ALL_CRC_MEMBERS',archive_SHA256=h.hexdigest(),archive_size=total,source='Only fresh independent409cloud downloads concatenated in frozen order; original local408archive/parts not read',members=1110,logical_files=2982,unique_payloads=1109,CRC_SHA256=True,parts=parts,start_timestamp=start,end_timestamp=time.time(),original408_operational_CPU='UNRESOLVED unchanged; new409resources separate')
with (W/'cloud-closure.json').open('x',encoding='utf8',newline='\n') as f:json.dump(record,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
with (W/'downloads/assembly-completion.json').open('x',encoding='utf8') as f:json.dump(dict(status='VERIFIED_ASSEMBLY_CRC_LOGICAL_FILES',receipt='cloud-closure.json'),f)
print('CLOUD408_CLOSURE',h.hexdigest(),total,'1110members/2982logicalfiles')
