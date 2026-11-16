"""Exact portable409.5 asset review; never a wildcard runtime/venv/key exception."""
import ast,base64,gzip,hashlib,io,json,pickletools,re,ssl,stat,tarfile,zipfile
from pathlib import Path,PurePosixPath,PureWindowsPath

TEXT={'.py','.ps1','.json','.csv','.md','.txt','.log','.toml','.yaml','.yml','.xml','.ini','.cfg','.c','.h','.html','.css','.cmd','.bat','.pth','._pth'}
PRIVATE={'agents.md','changes.md','development-plan.md','session-handoff.md','session-handoff-archive.md','context-manifest.json'}
CA_SHA='2089fc5a25836401faee99f722460b01b393999746a0fb817943666d6ecc0458'
PIL_SHA='e9601111f8817e8387fd792b3643e709a5a11febea43cb49de1732e776ba5f60'
URL_SHA='8e41819ee11a746dc7e704499fbdece7bbc609c2be0284cd29472c59ea98434c'

def require(ok,message):
    if not ok:raise ValueError(message)

def digest(b):return hashlib.sha256(b).hexdigest()

def safe_name(name):
    p=PurePosixPath(name);w=PureWindowsPath(name)
    require(not w.drive and not p.is_absolute() and '..' not in p.parts and '\\' not in name and
            ':' not in name and all(x not in ('','.','..') for x in p.parts),'Unsafe archive path')
    return p

def text_review(name,b,core):
    issue=core.inspect_stream(io.BytesIO(b))
    if not issue:return
    # Only exact known source bytes, not directories or filename extensions.
    if name=='runtime/Lib/site-packages/PIL/ImageFont.py' and digest(b)==PIL_SHA:
        hits=list(core.SECRET_BYTES.finditer(b));tree=ast.parse(b)
        literals=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and ast.unparse(n.func)=='base64.b64decode']
        for hit in hits:
            line=b[:hit.start()].count(b'\n')+1
            call=next(n for n in literals if n.lineno<=line<=n.end_lineno)
            font=base64.b64decode(ast.literal_eval(call.args[0]));require(font[:4]==b'\0\1\0\0','Not TTF data')
        return
    if name=='runtime/Lib/urllib/request.py' and digest(b)==URL_SHA:
        doc=ast.parse(b).body[0];require(isinstance(doc,ast.Expr) and isinstance(doc.value,ast.Constant),'Not public module docstring')
        require(all(doc.lineno<=b[:m.start()].count(b'\n')+1<=doc.end_lineno for m in core.SECRET_BYTES.finditer(b)),'Not doc example')
        return
    raise ValueError('Secret content: '+name)

def payload(name,b,core,depth=0):
    require(depth<=8 and len(b)<=128*1024**2,'Nested review budget')
    p=safe_name(name);suffix=p.suffix.lower()
    require(p.name.lower() not in PRIVATE and suffix not in {'.sqlite','.sqlite3','.db','.key','.pfx','.p12','.kdbx'},'Private/opaque payload')
    if core.SECRET_NAME.search(p.name):
        require(name=='runtime/Lib/ensurepip/_bundled/pip-25.3-py3-none-any.whl!pip/_vendor/certifi/cacert.pem' and digest(b)==CA_SHA,'Secret filename: '+name)
        require(b'PRIVATE KEY' not in b,'Private key')
        c=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);c.load_verify_locations(cadata=b.decode('ascii'))
        require(len(c.get_ca_certs(binary_form=True))==147,'Not qualified public CA')
        return
    if suffix in TEXT or p.name.endswith('._pth'):text_review(name,b,core)
    elif suffix in {'.zip','.whl','.npz'}:
        if not b:
            require(name=='runtime/Lib/site-packages/scipy-1.18.1-cp314-cp314t-win_amd64.whl','Unreviewed empty archive')
            return
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            require(z.testzip() is None,'Nested CRC failure');seen=set()
            for i in z.infolist():
                safe_name(i.filename);require(i.filename not in seen and not i.flag_bits&1 and not stat.S_ISLNK(i.external_attr>>16),'Unsafe nested member');seen.add(i.filename)
                require(not any(x.startswith(('.venv','venv')) or x=='__pycache__' for x in PurePosixPath(i.filename).parts),'Nested environment')
                if not i.is_dir():payload(name+'!'+i.filename,z.read(i),core,depth+1)
    elif suffix in {'.gz','.tgz','.tar'}:
        if suffix=='.tar':raw=b
        else:
            with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:raw=f.read(64*1024**2+1)
        require(len(raw)<=64*1024**2,'Gzip expansion limit')
        # Ordinary compressed datasets are data, not automatically tar archives.
        try:t=tarfile.open(fileobj=io.BytesIO(raw),mode='r:')
        except tarfile.ReadError:text_review(name+'!decoded',raw,core)
        else:
            with t:
                members=t.getmembers();names={i.name:i for i in members}
                require(len(names)==len(members),'Duplicate tar paths')
                for i in members:
                    safe_name(i.name)
                    if i.islnk():
                        require(name=='runtime/Lib/site-packages/dateutil/zoneinfo/dateutil-zoneinfo.tar.gz' and digest(b)=='d3ea52e7b6e968de0d884df1288193596fa95b803db4f92a18279a7398004475','Unreviewed tar hardlink')
                        seen={i.name};target=i
                        while target.islnk():
                            safe_name(target.linkname)
                            require(target.linkname in names and target.linkname not in seen,'Escaping/cyclic hardlink')
                            seen.add(target.linkname);target=names[target.linkname]
                        require(target.isfile(),'Hardlink does not resolve to regular data')
                        data=t.extractfile(target).read();require(data.startswith(b'TZif'),'Not qualified timezone alias data')
                        payload(name+'!'+i.name,data,core,depth+1)
                    else:
                        require(i.isfile() or i.isdir(),'Unsafe tar member')
                        if i.isfile():payload(name+'!'+i.name,t.extractfile(i).read(),core,depth+1)
    elif suffix in {'.pkl','.pickle'}:
        require(name=='runtime/Lib/site-packages/numpy/_core/tests/data/astype_copy.pkl' and digest(b)=='9564b309cbf3441ff0a6e4468fddaca46230fab34f15c77d87025a455bdf59d9','Unreviewed pickle')
        ops=list(pickletools.genops(b))  # Static opcode parsing, NEVER unpickle/execute.
        require(len(ops)==39 and ops[-1][0].name=='STOP' and ops[-1][2]==len(b)-1,'Unexpected pickle structure')
        require({a for op,a,pos in ops if op.name=='GLOBAL'}=={'numpy.core.multiarray _reconstruct','numpy ndarray','numpy dtype'},'Unexpected pickle globals')
        require(not any(op.name in {'STACK_GLOBAL','PERSID','BINPERSID','EXT1','EXT2','EXT4'} for op,a,pos in ops),'Dynamic pickle reference')
        text_review(name,b,core)
    elif suffix in {'.7z','.rar'}:raise ValueError('Opaque nested payload')

def review(archive,contract,pin,core):
    """Return None only for the authenticated complete allowlist, otherwise refuse."""
    try:
        contract=Path(contract);raw=contract.read_bytes();require(digest(raw)==pin,'Asset contract SHA')
        m=json.loads(raw);require(m['kind']=='portable040-asset-review-v1','Wrong asset contract')
        archive=Path(archive);require(archive.stat().st_size==m['archive_size'],'Archive size')
        require(core.sha(archive)==m['archive_SHA256'],'Archive SHA')
        require(m['original409_SHA256']=='74247a863bd1c445ecfa736e1a0df60db43ad541cb34d7df5de909410781f3bd','Wrong baseline')
        with zipfile.ZipFile(archive) as z:
            require(z.testzip() is None,'CRC');seen=set()
            for i in z.infolist():
                n=safe_name(i.filename);require(i.filename not in seen and not i.flag_bits&1 and not stat.S_ISLNK(i.external_attr>>16),'Duplicate/encrypted/symlink');seen.add(i.filename)
                require(n.parts[0]==m['root'] and len(n.parts)>1,'Wrong ZIP root')
                rel=PurePosixPath(*n.parts[1:]).as_posix();require(rel in m['files'],'Unlisted file: '+rel)
                b=z.read(i);require(digest(b)==m['files'][rel]['sha256'] and len(b)==m['files'][rel]['size'],'Asset changed: '+rel)
                # A real developer environment is never admitted by a directory wildcard.
                if any(x.startswith(('.venv','venv')) for x in PurePosixPath(rel).parts):
                    require(rel.startswith('runtime/Lib/venv/') and m['files'][rel]['role']=='qualified-CPython-stdlib','Developer environment')
                require('__pycache__' not in n.parts and not rel.endswith('pyvenv.cfg'),'Developer environment/cache')
                if rel.endswith(('.exe','.dll','.pyd')):require(m['files'][rel]['role'] in {'qualified-runtime','qualified-CPython-stdlib'} and b[:2]==b'MZ','Unverified binary')
                payload(rel,b,core)
            require({PurePosixPath(*PurePosixPath(n).parts[1:]).as_posix() for n in seen}==set(m['files']),'Incomplete package')
        return None
    except Exception as exc:return type(exc).__name__+': '+str(exc)
