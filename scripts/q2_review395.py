"""Offline394 evidence audit; no solver, code execution or source modification."""
import hashlib
import json
import math
from pathlib import Path,PurePosixPath
from decimal import Decimal,localcontext
from fractions import Fraction
import zipfile

PATCH_SHA256='df958f9f4c41ad9f3ed57ec2851c30de8b55e608287bd4ebeecfb2f902abbdc6'
ARCHIVE_SHA256='4182055bebe7214eadaf3ed4cc234de5fd675f0eafdd3c589e2583c05f466520'


def read_archive(path,expected_sha=ARCHIVE_SHA256):
    """Authenticate and return frozen members; never extract or execute them."""
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError('Archive SHA mismatch')
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate archive members')
        for name in names:
            p=PurePosixPath(name.replace('\\','/'))
            if p.is_absolute() or '..' in p.parts or ':' in name:raise ValueError('Unsafe archive member')
        if sum(i.file_size for i in z.infolist())>32*1024**2:raise ValueError('Bounded394 archive too large')
        manifest=json.loads(z.read('STAGE394-MANIFEST.json'));members={}
        for row in manifest['files']:
            b=z.read(row['path'])
            if len(b)!=row['size'] or hashlib.sha256(b).hexdigest()!=row['sha256']:raise ValueError('Member SHA mismatch')
            members[row['path']]=b
        if set(names)!=set(members)|{'STAGE394-MANIFEST.json','RESTORE.txt'}:raise ValueError('Unmanifested archive content')
    return manifest,members


def _time(x):
    if type(x) not in (int,float):raise ValueError('Timing must be builtin real, excluding bool')
    try:x=float(x)
    except OverflowError as e:raise ValueError('Nonfinite timing') from e
    if not math.isfinite(x) or x<=0:raise ValueError('Invalid wall time')
    return Decimal.from_float(x)


def timing_audit(series):
    """Independent exact-binary timing sums/medians, not394 paired_summary."""
    if type(series) is not list or len(series)!=5:raise ValueError('Exactly five fixed series required')
    order=['ABBA','BAAB','ABBA','BAAB','ABBA'];cases=['one-python','two-python','one-rust','two-rust']
    with localcontext() as ctx:
        ctx.prec=80;out={};losers=[]
        for level in ('micro','macro'):
            pairs={case:[] for case in cases};aggregate=[]
            for index,run in enumerate(series):
                if run['series']!=index or run['order']!=order[index] or [r['id'] for r in run['rows']]!=cases:raise ValueError('Series/order/cases changed')
                total=[Decimal(0),Decimal(0)]
                for row in run['rows']:
                    samples=row[level]
                    if ''.join(x['role'] for x in samples)!=order[index]:raise ValueError('Not the declared paired order')
                    wrong=any(x['calls']!=512 for x in samples) if level=='micro' else any(x['rollouts']!=8 or x['packets_per_rollout']!=2 for x in samples)
                    if wrong:raise ValueError('Workload changed')
                    a=sum((_time(x['wall_seconds']) for x in samples if x['role']=='A'),Decimal(0))
                    b=sum((_time(x['wall_seconds']) for x in samples if x['role']=='B'),Decimal(0))
                    pairs[row['id']].append((a,b));total=[total[0]+a,total[1]+b]
                    if a<b:losers.append(dict(level=level,case=row['id'],series=index,speedup=float(a/b),prototype_time_increase_fraction=float(b/a-1)))
                aggregate.append(tuple(total))
            def describe(values):
                median=lambda v:sorted(v)[2]
                ratios=[a/b for a,b in values];savings=[a-b for a,b in values];positive=sum(a>b for a,b in values);n=sum(a!=b for a,b in values)
                p=Fraction(sum(math.comb(n,k) for k in range(positive,n+1)),2**n)
                return dict(median_baseline=float(median([a for a,b in values])),median_prototype=float(median([b for a,b in values])),median_paired_saving=float(median(savings)),median_speedup=float(median(ratios)),minimum_speedup=float(min(ratios)),maximum_speedup=float(max(ratios)),positive_series=positive,sign_p_exact=str(p),paired_times_decimal=[[str(a),str(b)] for a,b in values])
            out[level]=dict(aggregate=describe(aggregate),cases={case:describe(values) for case,values in pairs.items()})
    return dict(levels=out,losing_case_series=losers,independence='Separate workers do not establish stochastic independence; shared Windows scheduling/caches. Do not multiply micro/macro p-values.',new_benchmarks=0)
