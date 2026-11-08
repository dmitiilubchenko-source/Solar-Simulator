"""Read-only authentication/shape adapter for two historical point results400.

Container provenance authenticates historical inputs/code/payloads together.
It does not invent missing runtime counters or execute archived source.
"""
import ast
import hashlib
import io
import json
import math
from pathlib import Path,PurePosixPath
import struct
import zipfile

BASE='f723a2162b4e115378959e244f428529be2d4516'
CANDIDATE='a99f73a4adce95be9d264d8c403e0e6768a54cd7'
ARCHIVE_SHA='bcccf57600fa12057599c816cd7d8bd064015f4ae74af055b62c70d1e76b921f'
HELPER='qualification400/executed-check_candidate400.py'


def canonical(value):return json.dumps(value,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf8')
def sha(data):return hashlib.sha256(data).hexdigest()


def logical_path(path):
    p=PurePosixPath(path.replace('\\','/'))
    if p.is_absolute() or '..' in p.parts or ':' in str(p):raise ValueError('Unsafe logical archive reference')
    return str(p)


def tool_digest(mapping,name):
    normalized={}
    for path,digest in mapping.items():
        key=logical_path(path)
        if key in normalized:raise ValueError('Ambiguous normalized tool metadata path')
        normalized[key]=digest
    if name not in normalized:raise ValueError('Required historical tool binding missing')
    return normalized[name]


def authenticated_archive(path):
    raw=Path(path).read_bytes()
    if sha(raw)!=ARCHIVE_SHA:raise ValueError('Historical400 archive SHA mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or sum(x.file_size for x in z.infolist())>16*1024**2:raise ValueError('Invalid archive inventory/size')
        for name in names:
            p=PurePosixPath(name.replace('\\','/'))
            if p.is_absolute() or '..' in p.parts or ':' in name:raise ValueError('Unsafe archive path')
        if z.testzip() is not None:raise ValueError('Archive CRC mismatch')
        manifest=json.loads(z.read('MANIFEST.json'));members={}
        for row in manifest['files']:
            data=z.read(row['path'])
            if len(data)!=row['size'] or sha(data)!=row['sha256']:raise ValueError('Archived member mismatch')
            members[row['path']]=data
        if set(names)!=set(members)|{'MANIFEST.json','RESTORE.txt'}:raise ValueError('Unmanifested archive member')
    core=json.loads(members['qualification400/report-core.json']);plan=json.loads(members['qualification400/execution-plan.json'])
    if manifest['candidate_commit']!=CANDIDATE or core['base_commit']!=BASE or core['candidate_commit']!=CANDIDATE or plan['base_commit']!=BASE:raise ValueError('Wrong historical source binding')
    helper_hash=tool_digest(core['tools_SHA256'],'.tools/qualification400-20261108/executed-check_candidate400.py')
    if sha(members[HELPER])!=helper_hash:raise ValueError('Historical helper SHA mismatch')
    calls=[n for n in ast.walk(ast.parse(members[HELPER])) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='advance']
    if len(calls)!=3 or any(len(n.args)!=2 or not isinstance(n.args[1],ast.Constant) or n.args[1].value!=1 for n in calls):raise ValueError('Unexpected historical per-case advance control flow')
    return manifest,members,dict(archive_SHA256=ARCHIVE_SHA,helper_SHA256=helper_hash,base_commit=BASE,candidate_commit=CANDIDATE,
        statically_proven_per_completed_case_advance_calls=3,
        counter_scope='3 source-level advance calls, not a historical measured nfev/RHS count; point DOP path must independently establish one solve per advance')


def vector(values,width):
    if type(values) is not list or len(values)!=width:raise ValueError('Wrong vector width')
    out=bytearray()
    for v in values:
        if type(v) not in (float,int):raise ValueError('Non-real/bool raw value')
        try:value=float(v)
        except OverflowError as error:raise ValueError('Overflow raw value') from error
        if not math.isfinite(value):raise ValueError('Nonfinite raw value')
        out.extend(struct.pack('<d',value))
    return bytes(out)


def physical_bits(documents):
    """Actual saved p/v/q/S binary64, including counts/order; never normalizes."""
    out=bytearray()
    for d in documents:
        bodies=d['bodies'];rot=d.get('rotations',[])
        out.extend(struct.pack('<II',len(bodies),len(rot)))
        for b in bodies:
            for key in ('position','velocity','spin'):out.extend(vector(b[key],3))
        for r in rot:
            out.extend(vector(r['quaternion'],4));out.extend(vector(r['angular_momentum'],3))
    return bytes(out)


def validate_legacy_point(payload,checkpoint,expected):
    if set(payload)!={'case','backend','epochs_seconds','documents','legacy_initial','native_calls','resume_exact'}:raise ValueError('Wrong legacy payload schema')
    backend=expected['settings']['backend']
    if payload['case']!='point' or payload['backend']!=backend or backend not in ('python','rust'):raise ValueError('Wrong case/backend')
    if payload['epochs_seconds']!=[0.,2.,4.] or len(payload['documents'])!=3 or payload['resume_exact'] is not True:raise ValueError('Incomplete epochs/resume')
    docs=payload['documents']
    if canonical(docs[0])!=canonical(expected):raise ValueError('Historical IC/settings mismatch')
    for t,d in zip((0.,2.,4.),docs):
        if d['time']!=t or d['units']!='SI' or d.get('rotations') or d.get('initial_rotations'):raise ValueError('Wrong point state/time/units')
        for key in ('settings','initial','schema_version','model','origin'):
            if canonical(d[key])!=canonical(expected[key]):raise ValueError('Changed legacy invariant input '+key)
        if len(d['bodies'])!=len(expected['bodies']):raise ValueError('Body inventory mismatch')
        for a,b in zip(d['bodies'],expected['bodies']):
            if any(a[k]!=b[k] for k in ('name','mass','radius','spin')):raise ValueError('Changed body identity/parameter')
    if canonical(checkpoint)!=canonical(docs[1]):raise ValueError('Checkpoint does not belong to exact second frame')
    calls=payload['native_calls']
    if type(calls) is not int or calls<0 or (calls!=0 if backend=='python' else calls==0):raise ValueError('Wrong native counter')
    bits=physical_bits(docs)
    return dict(status='AUTHENTICATED_HISTORICAL_POINT_INPUT_AND_RAW_STATE',backend=backend,
        raw_binary64_SHA256=sha(bits),initial_SHA256=sha(canonical(expected)),frames=3,
        recorded_native_calls=calls,historical_solver_calls_measured=None,historical_nfev=None,
        inferred_source_level_advance_calls=3,physical_accuracy_certified=False)
