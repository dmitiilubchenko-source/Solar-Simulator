"""Independent comparison to old409 bytes, NEW ZIP and authenticated asset contract."""
from pathlib import Path
import hashlib,json,stat,sys,zipfile
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116');F=W/'SolarSimulator-0.4.0-4095'
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
old=json.loads((R/'scripts/qualification409/zip-members.json').read_bytes())
newfiles={f.relative_to(F).as_posix():f for f in F.rglob('*') if f.is_file()}
oldfiles={x['path']:x for x in old['members']}
changed=[n for n in oldfiles if sha(newfiles[n])!=oldfiles[n]['SHA256']]
assert changed==['Physics Verification.cmd'],changed
added=set(newfiles)-set(oldfiles)
assert added=={'CURRENT-040-VERIFICATION.json','verification-current040/manifest-v1.json','verification-current040/recompute_current040_v1.py','verification-current040/README.md'},added
assert not (set(oldfiles)-set(newfiles))
runtime=json.loads((Path('C:/Users/Admin/Documents/Codex/Solar409-build-20261111')/'runtime-content-audit.json').read_bytes())
assert all(sha(F/'runtime'/n)==v for n,v in runtime['all_runtime_files'].items())
dest=W/'SolarSimulator-0.4.0-20261116-4095.zip'
with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
    for n,f in sorted(newfiles.items()):z.write(f,F.name+'/'+n)
rows={}
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    for i in z.infolist():
        p=Path(i.filename);assert not p.is_absolute() and '..' not in p.parts and not stat.S_ISLNK(i.external_attr>>16)
        n='/'.join(p.parts[1:]);b=z.read(i);assert hashlib.sha256(b).hexdigest()==sha(newfiles[n])
        role='qualified-CPython-stdlib' if n.startswith('runtime/Lib/venv/') else 'qualified-runtime' if n.startswith('runtime/') else 'public-resource'
        rows[n]=dict(size=len(b),sha256=hashlib.sha256(b).hexdigest(),CRC32=f'{i.CRC:08x}',role=role)
contract=dict(kind='portable040-asset-review-v1',archive_SHA256=sha(dest),archive_size=dest.stat().st_size,root=F.name,files=rows,original409_SHA256=old['archive_SHA256'],provenance='Every old member independently compared to sealed409; runtime closure previously authenticated against qualified CPython/distributions/wheels; only one old CMD changed and four current verification assets added')
(W/'asset-contract.json').write_text(json.dumps(contract,indent=2)+'\n',encoding='utf8')
(W/'new-package.json').write_text(json.dumps(dict(archive=str(dest),archive_SHA256=sha(dest),archive_size=dest.stat().st_size,member_count=len(rows),changed_old=changed,added=sorted(added),runtime_unchanged=True,asset_contract_SHA256=sha(W/'asset-contract.json'),source_commit='237f73612c3c159acf92b32a15cf0289958fd921',full410_executed=False),indent=2)+'\n')
print('NEW_ZIP_AND_INDEPENDENT_MINIMAL_DIFF_PASS',dest.stat().st_size,len(rows))
