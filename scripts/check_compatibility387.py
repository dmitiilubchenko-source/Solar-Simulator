"""Read-only portable verifier and independent cross-version state observer.

This module never integrates. The stage387 acquisition was resource-stopped
before IC creation; its exact attempted worker is preserved in the raw bundle.
The observer deliberately imports no Solar numerical implementation.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zipfile


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def tree(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def verify_portable(archive, directory, expected):
    """Verify original ZIP and every installed member, without extraction/writes."""
    if sha(archive) != expected:
        raise ValueError('Original accepted ZIP SHA mismatch')
    members = {}
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            full = item.filename.replace('\\', '/')
            prefix = directory.name+'/'
            if not full.startswith(prefix): raise ValueError('Unexpected archive root')
            name = full[len(prefix):]
            p = (directory/name).resolve()
            if not p.is_relative_to(directory.resolve()) or name in members:
                raise ValueError('Unsafe/duplicate ZIP member')
            if item.is_dir():
                continue
            with z.open(item) as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()  # reads/checks CRC too
            if not p.is_file() or p.stat().st_size != item.file_size or sha(p) != digest:
                raise ValueError('Installed portable member mismatch: '+name)
            members[name] = dict(bytes=item.file_size, SHA256=digest)
    extras = sorted(set(tree(directory))-members.keys())
    # Bytecode caches are not executed: -B plus a fresh external pycache_prefix.
    if any('__pycache__' not in Path(name).parts for name in extras):
        raise ValueError('Unverified extra portable files: '+repr(extras[:10]))
    return dict(archive_bytes=archive.stat().st_size, archive_SHA256=expected,
                members=members, excluded_bytecode_extras=extras)


def vector(b,key):return b[key]
def dot(a,b):return math.fsum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def invariants(document, G):
    """Independent Newton/MacCullagh observer: fsum and body-frame inertia.

    Scalar-first quaternion rotates body to inertial. SI: E J, P kg m/s,
    L kg m²/s. No runtime evaluator or cached PASS flags used.
    """
    bodies=document['bodies'];energy=[]
    p=[math.fsum(b['mass']*b['velocity'][k] for b in bodies) for k in range(3)]
    l=[math.fsum(b['mass']*cross(b['position'],b['velocity'])[k]+b['spin'][k] for b in bodies) for k in range(3)]
    for i,b in enumerate(bodies):
        energy.append(.5*b['mass']*dot(b['velocity'],b['velocity']))
        for c in bodies[i+1:]:energy.append(-G*b['mass']*c['mass']/math.dist(b['position'],c['position']))
    for rot in document.get('rotations',[]):
        w,x,y,z=rot['quaternion']
        mat=[[1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)],
             [2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)],
             [2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]]
        moments=rot['figure']['moments'];s=rot['angular_momentum']
        body_s=[math.fsum(mat[j][k]*s[j] for j in range(3)) for k in range(3)]
        energy.append(.5*math.fsum(body_s[k]**2/moments[k] for k in range(3)))
        l=[l[k]+s[k] for k in range(3)]
        source=next(b for b in bodies if b['name']==rot['body'])
        for b in bodies:
            if b is source:continue
            delta=[b['position'][k]-source['position'][k] for k in range(3)];r=math.hypot(*delta)
            n=[d/r for d in delta];nb=[math.fsum(mat[j][k]*n[j] for j in range(3)) for k in range(3)]
            energy.append(G*b['mass']*(3*math.fsum(moments[k]*nb[k]**2 for k in range(3))-math.fsum(moments))/(2*r**3))
    return dict(E_J=math.fsum(energy),P_kg_m_s=p,L_kg_m2_s=l)


def state_bytes(document):
    values=[document['time']]
    for b in document['bodies']:
        values.extend([b['mass'],b['radius'],*b['position'],*b['velocity'],*b['spin']])
    for rot in document.get('rotations',[]):values.extend([*rot['quaternion'],*rot['angular_momentum']])
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in values):
        raise ValueError('Nonfinite or unsupported state scalar')
    return b''.join(struct.pack('>d',float(x)) for x in values)


def observe(root):
    binding=root/'ic-binding.json'
    if binding.exists():assert sha(root/'plan.json')==read(binding)['plan_SHA256']
    plan=read(root/'plan.json');rows=[]
    for case in plan['cases']:
        old=read(root/'accepted'/case['id']/'frames.json');new=read(root/'candidate'/case['id']/'frames.json')
        assert len(old)==len(new)==4
        assert [d['time'] for d in old]==[d['time'] for d in new]==case['epochs_seconds']
        row=dict(id=case['id'],settings_exact=True,initial_exact=True,state_bits_exact=True,documents_exact=True,
                 max_position_difference_m=0.,max_velocity_difference_m_s=0.,invariants=[])
        for a,b in zip(old,new):
            assert len(a['bodies'])==len(b['bodies'])
            row['settings_exact'] &= a['settings']==b['settings'];row['initial_exact'] &= a['initial']==b['initial']
            row['state_bits_exact'] &= state_bytes(a)==state_bytes(b);row['documents_exact'] &= a==b
            for x,y in zip(a['bodies'],b['bodies']):
                assert x['name']==y['name']
                row['max_position_difference_m']=max(row['max_position_difference_m'],math.dist(x['position'],y['position']))
                row['max_velocity_difference_m_s']=max(row['max_velocity_difference_m_s'],math.dist(x['velocity'],y['velocity']))
            ia,ib=invariants(a,float.fromhex(plan['G_hex'])),invariants(b,float.fromhex(plan['G_hex']))
            row['invariants'].append(dict(time_seconds=a['time'],accepted=ia,candidate=ib,equal=ia==ib))
        row['status']='EXACT' if all(row[k] for k in ('settings_exact','initial_exact','state_bits_exact','documents_exact')) else 'UNRESOLVED_DIFFERENCE'
        rows.append(row)
    save(root/'comparison.json',dict(cases=rows,physical_accuracy_claim=False,inputs_unchanged=tree(root/'inputs')==plan['inputs_SHA256']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['verify','observe'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--portable',type=Path);parser.add_argument('--archive',type=Path)
    args=parser.parse_args()
    if args.action=='verify':save(args.root/'portable-verification.json',verify_portable(args.archive,args.portable,'7c578220ec77e792aa9589f32a30352e88277d0d096bff0ad3ca5aae9c014c49'))
    else:observe(args.root)


if __name__=='__main__':main()
