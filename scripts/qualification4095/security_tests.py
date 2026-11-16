"""Full asset review and synthetic failures; original and new ZIP remain immutable."""
from pathlib import Path
import hashlib,importlib.util,io,json,sys,zipfile
from scripts.qualification4095 import portable_review as s
W=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116');BASE=Path('C:/Users/Admin/Documents/Codex/2026-10-29/files-pasted-by-the-user-codex/outputs');sys.path.insert(0,str(BASE));import backup_core as core
a=json.loads((W/'new-package.json').read_bytes());contract=W/'asset-contract.json'
issue=s.review(a['archive'],contract,a['asset_contract_SHA256'],core);assert issue is None,issue
rows=[];fixtures=W/'security-fixtures';fixtures.mkdir(exist_ok=False)
def reject(label,name,b,role='public-resource',symlink=False,canonical=False):
    archive=fixtures/(label+'.zip')
    with zipfile.ZipFile(archive,'x') as z:
        i=zipfile.ZipInfo('test/'+name)
        if symlink:i.external_attr=(0o120777<<16)
        z.writestr(i,b)
    files=json.loads(contract.read_bytes())['files'] if canonical else {name:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest(),role=role)}
    m=dict(kind='portable040-asset-review-v1',root='test',archive_SHA256=core.sha(archive),archive_size=archive.stat().st_size,original409_SHA256=safe409,files=files)
    f=fixtures/(label+'.json');f.write_text(json.dumps(m));result=s.review(archive,f,core.sha(f),core)
    assert result,label;rows.append(dict(case=label,rejected=True,reason=result))
safe409='74247a863bd1c445ecfa736e1a0df60db43ad541cb34d7df5de909410781f3bd'
key=b'-----BEGIN '+b'PRIVATE KEY-----\nsynthetic\n-----END PRIVATE KEY-----'
token=b'AKIA'+b'A'*16
reject('private-key-PEM','runtime/Lib/public.pem',key)
reject('credentials-in-Python','runtime/Lib/credential.py',token)
reject('unknown-stdlib','runtime/Lib/unknown.py',b'pass\n',canonical=True)
reject('changed-wheel','runtime/Lib/ensurepip/_bundled/pip-25.3-py3-none-any.whl',b'changed',canonical=True)
reject('changed-resource','runtime/Lib/site-packages/PIL/ImageFont.py',b'changed',canonical=True)
reject('symlink','docs/link',b'outside',symlink=True)
reject('path-traversal','../escape',b'bad')
reject('developer-env','runtime/Lib/venv/unknown.py',b'pass\n',role='qualified-runtime')
reject('sqlite','data/user.sqlite',b'SQLite format 3\0')
reject('private-context','docs/AGENTS.md',b'private context')
nested=io.BytesIO()
with zipfile.ZipFile(nested,'w') as z:z.writestr('../escape',b'bad')
reject('unsafe-nested','data/assets.zip',nested.getvalue())
reject('unverified-binary','runtime/Lib/unknown.pyd',b'MZsynthetic')
reject('secret-in-public-directory','docs/usage.py',token)
try:s.payload('runtime/Lib/ensurepip/_bundled/pip-25.3-py3-none-any.whl!pip/_vendor/certifi/cacert.pem',b'changed publicCA',core)
except ValueError:rows.append(dict(case='changed-public-CA',rejected=True))
else:raise AssertionError('Changed CA admitted')
assert s.review(a['archive'],contract,'0'*64,core) is not None
rows.append(dict(case='wrong-contract-pin',rejected=True))
(W/'security-results.json').write_text(json.dumps(dict(full_real_package_review='PASS',security_negatives=rows,permanent_global_exceptions_added=False,scanner_SHA256=core.sha(Path(s.__file__)),contract_SHA256=core.sha(contract)),indent=2)+'\n')
print('FULL_CLOSED_ASSET_REVIEW_PASS; security negatives',len(rows))
