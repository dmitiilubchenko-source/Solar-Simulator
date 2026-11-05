"""Independent saved-state metric arithmetic; no solver/production imports."""
import math
import hashlib
import json
from pathlib import Path
from decimal import Decimal,localcontext
from fractions import Fraction


def norm(values):
    return math.sqrt(math.fsum(float(x)*float(x) for x in values))


def exact_norm_difference(a,b):
    """Exact rational subtraction/squares of saved binary64, Decimal sqrt."""
    squares=sum((Fraction.from_float(float(x))-Fraction.from_float(float(y)))**2 for x,y in zip(a,b))
    with localcontext() as ctx:
        ctx.prec=90
        return float((Decimal(squares.numerator)/Decimal(squares.denominator)).sqrt())


def matrix_decimal(q):
    """Normalized quaternion rotation; algebraic division by norm², not sqrt."""
    w,x,y,z=[Decimal.from_float(float(v)) for v in q]
    n=w*w+x*x+y*y+z*z
    if n==0:raise ValueError('Zero quaternion')
    return [1-2*(y*y+z*z)/n,2*(x*y-w*z)/n,2*(x*z+w*y)/n,
        2*(x*y+w*z)/n,1-2*(x*x+z*z)/n,2*(y*z-w*x)/n,
        2*(x*z-w*y)/n,2*(y*z+w*x)/n,1-2*(x*x+y*y)/n]


def orientation_arithmetic(qa,qb,Ra,Rb,precision=70):
    """Angle uses exact normalized inputs then atan2; invariant under q→−q.

    Decimal matrix distance and chord are comparisons of saved states, never
    claims about their distance from an exact physical trajectory.
    """
    with localcontext() as ctx:
        ctx.prec=precision
        a=matrix_decimal(qa);b=matrix_decimal(qb)
        root=lambda x:sum(v*v for v in x).sqrt()
        f=root([x-y for x,y in zip(a,b)])
        qa=[Decimal.from_float(float(v)) for v in qa];qb=[Decimal.from_float(float(v)) for v in qb]
        na=root(qa);nb=root(qb)
        if not na or not nb:raise ValueError('Zero quaternion')
        qa=[v/na for v in qa];qb=[v/nb for v in qb]
        if sum(x*y for x,y in zip(qa,qb))<0:qb=[-v for v in qb]
        chord=root([x-y for x,y in zip(qa,qb)])
        # theta=4*asin(chord/2); stable even below sqrt(binary64 epsilon).
        theta=4*math.asin(min(1.,float(chord/2)))
        defects=[float(root([Decimal.from_float(float(x))-y for x,y in zip(raw,exact)])) for raw,exact in ((Ra,a),(Rb,b))]
        return dict(matrix_frobenius_from_q=float(f),angle_rad=theta,normalised_q_chord=float(chord),
            representation_defects=defects)


def compare(a,b,document,times):
    """Scalar reductions and per-body maxima, same historical scales."""
    p=[x['position'] for x in document['bodies']];v=[x['velocity'] for x in document['bodies']]
    lengths=[norm([x-y for x,y in zip(p[i],p[j])]) for i in range(len(p)) for j in range(i)]
    speeds=[norm([x-y for x,y in zip(v[i],v[j])]) for i in range(len(v)) for j in range(i)]
    spin=[norm(x['angular_momentum']) for x in document['rotations']]
    names=[x['name'] for x in document['bodies']];rot=[x['body'] for x in document['rotations']]
    result={}
    for field,label,scales,body_names in [('positions','position',[max(lengths)]*len(p),names),
        ('velocities','velocity',[max(speeds)]*len(p),names),('orientation','orientation',[1.]*len(rot),rot),
        ('spins','spin',spin,rot),('quaternions','quaternion_raw',[1.]*len(rot),rot)]:
        if field not in a or field not in b:continue
        best=None;per_body=[];series=[]
        for j,(scale,name) in enumerate(zip(scales,body_names)):
            local=None
            for i,t in enumerate(times):
                x=a[field][i,j].reshape(-1);y=b[field][i,j].reshape(-1)
                delta=[float(aa)-float(bb) for aa,bb in zip(x,y)];raw=norm(delta);value=raw/scale
                row=dict(value=value,raw_SI_or_dimensionless=raw,scale=scale,body=name,index=i,time_seconds=float(t),
                    largest_component=int(max(range(len(delta)),key=lambda k:abs(delta[k]))),delta=delta)
                if local is None or value>local['value']:local=row
                series.append(dict(body=name,index=i,value=value))
            per_body.append(local)
            if best is None or local['value']>best['value']:best=local
        result[label]=dict(maximum=best,per_body=per_body,series=series)
    result['historical_aggregate']=max(result[k]['maximum']['value'] for k in ('position','velocity','orientation','spin'))
    return result


def audit_saved(root):
    """Replay four historical comparisons from pinned Git data; never evolve."""
    import numpy as np
    root=Path(root)
    pinned={'scripts/two-q2-380-completion-plan.json':'b93c534e6b38aedc82df70768f1c471963093645f700e20c741ec87fa6fffb13',
        'scripts/validation/two-q2-380.npz':'51e7c79d7a36547df92959a8614d9d5804232d39c0ebfe5c4a143ecdd6da696a'}
    for name,h in pinned.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=h:raise ValueError('Historical input SHA mismatch: '+name)
    plan=json.loads((root/'scripts/two-q2-380-completion-plan.json').read_bytes())
    rows=[]
    with np.load(root/'scripts/validation/two-q2-380.npz',allow_pickle=False) as archive:
        for case in plan['cases']:
            for backend in plan['backends']:
                values=[]
                for level in plan['levels']:
                    prefix=case['id']+'__'+backend+'__'+level['id']+'__'
                    value={k[len(prefix):]:archive[k] for k in archive.files if k.startswith(prefix)}
                    if not value or not all(np.isfinite(v).all() for v in value.values()):raise ValueError('Missing/nonfinite historical state')
                    values.append(value)
                coarse=compare(values[0],values[2],case['initial'],case['epochs'])
                standard=compare(values[1],values[2],case['initial'],case['epochs'])
                compact=lambda value:{k:({s:v for s,v in x.items() if s!='series'} if isinstance(x,dict) else x) for k,x in value.items()}
                rows.append(dict(case=case['id'],backend=backend,coarse_fine=compact(coarse),standard_fine=compact(standard),
                    original_criterion_pass=standard['historical_aggregate']<coarse['historical_aggregate']))
    return dict(stage=392,kind='Pinned saved-state arithmetic, not runtime qualification',inputs_SHA256=pinned,rows=rows,
        numerical_integrations=0,reference_in_original_convergence_criterion=False)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=audit_saved(args.root)
    with args.output.open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
