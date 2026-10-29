"""Offline evidence audit. No integration; remeasure arrays, never trust PASS flags."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.release_history import evidence_path

ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def errors(a,b,initial):
    """Independent scale selection/Euclidean reductions from physical inputs."""
    p=np.asarray([x['position'] for x in initial['bodies']]);v=np.asarray([x['velocity'] for x in initial['bodies']])
    lengths=[np.sqrt(np.dot(p[i]-p[j],p[i]-p[j])) for i in range(len(p)) for j in range(i)]
    speeds=[np.sqrt(np.dot(v[i]-v[j],v[i]-v[j])) for i in range(len(v)) for j in range(i)]
    norm=lambda x:np.sqrt(np.einsum('...i,...i->...',x,x))
    R=a['orientation']-b['orientation']
    return dict(position=float(norm(a['positions']-b['positions']).max()/max(lengths)),
        velocity=float(norm(a['velocities']-b['velocities']).max()/max(speeds)),
        orientation=float(np.sqrt(np.einsum('...ij,...ij->...',R,R)).max()),
        spin=float((norm(a['spins']-b['spins'])/[np.sqrt(np.dot(x['angular_momentum'],x['angular_momentum'])) for x in initial['rotations']]).max()))


def audit(root=ROOT):
    read=lambda name:json.loads((root/name).read_bytes())
    p=read('scripts/two-q2-380-completion-plan.json');r=read('docs/two-q2-380-validation.json')
    first=read('docs/two-q2-380-initial.json');continuation=p['continuation']
    assert r['plan_SHA256']==digest(root/'scripts/two-q2-380-completion-plan.json')
    assert first['plan_SHA256']==digest(root/'scripts/two-q2-380-plan.json')
    for name in ('result','arrays','original_plan'):
        assert digest(evidence_path(root,continuation[name]))==continuation[name+'_SHA256']
    assert r['arrays_SHA256']==digest(root/'scripts/validation/two-q2-380.npz')
    assert first['arrays_SHA256']==digest(root/'scripts/validation/two-q2-380-initial.npz')
    assert r['failure'] is None and len(r['rows'])==12 and len(r['continuous_convergence'])==2
    with np.load(root/'scripts/validation/two-q2-380.npz',allow_pickle=False) as data, np.load(root/'scripts/validation/two-q2-380-initial.npz',allow_pickle=False) as old:
        for key in old.files:assert np.array_equal(data[key],old[key]),key
        get=lambda prefix:{key[len(prefix):]:data[key] for key in data.files if key.startswith(prefix)}
        agreement=[];failures=[];allmetrics=[]
        for case in p['cases']:
            ident=case['id'];initial=case['initial'];ref=get(ident+'__reference1__')
            gap=errors(ref,get(ident+'__reference0__'),initial)
            assert max(gap.values())<p['criteria']['reference_uncertainty']
            for backend in p['backends']:
                values=[]
                for level in p['levels']:
                    actual=get(ident+'__'+backend+'__'+level['id']+'__');values.append(actual)
                    assert actual['positions'].shape==(65,len(initial['bodies']),3)
                    assert actual['quaternions'].shape==(65,2,4)
                    assert all(np.isfinite(v).all() for v in actual.values())
                    measured=errors(actual,ref,initial)
                    row=next(x for x in r['rows'] if (x['case'],x['backend'],x['level'])==(ident,backend,level['id']))
                    for key in measured:assert np.isclose(measured[key],row['reference_difference'][key],rtol=2e-14,atol=1e-30)
                    qnorm=float(np.max(np.abs(np.sqrt(np.einsum('...i,...i->...',actual['quaternions'],actual['quaternions']))-1)))
                    assert abs(qnorm-row['quaternion_norm'])<5e-16
                    assert qnorm<p['criteria']['quaternion_norm']
                    allmetrics.append(dict(case=ident,backend=backend,level=level['id'],reference=measured))
                coarse=errors(values[0],values[2],initial);standard=errors(values[1],values[2],initial)
                if max(standard.values())>=max(coarse.values()):failures.append(dict(case=ident,backend=backend,criterion='packet_tolerance_convergence'))
            continuous=[get(ident+'__continuous__'+x['id']+'__') for x in p['levels']]
            coarse=errors(continuous[0],continuous[2],initial);standard=errors(continuous[1],continuous[2],initial)
            assert max(standard.values())<max(coarse.values())
            for level in p['levels']:
                agreement.append(dict(case=ident,level=level['id'],difference=errors(get(ident+'__python__'+level['id']+'__'),get(ident+'__rust__'+level['id']+'__'),initial)))
        assert failures==r['failed_criteria']
    return dict(independent_array_audit=True,original_arrays_unchanged=True,rows=allmetrics,
        backend_agreement=agreement,retained_FAIL=failures,
        limitations='Euclidean reductions independently coded. Shared archived inputs/scales and physical assumptions; independent RK45 is numerical, not a rigorous exact oracle. This audit runs no solver and does not requalify current annual runtime.')


if __name__=='__main__':print(json.dumps(audit(),indent=2))
