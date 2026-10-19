"""Decimal directional identities of separate Newton/PN/figure Noether parts.

Developer diagnostics only. Decimal shifts never pass through float64.
Scalar EIH forces, analytic canonical parts and finite differences are separate
paths; the last two are compared against the action-Hessian source expression.
"""
from decimal import Decimal, localcontext

import numpy as np

from solar_simulator.simulation import G
from solar_simulator.relativity import C

ZERO = Decimal(0)
STEPS = ('1e-3','1e-5','1e-7')
CHANNELS = ('newton','pn_linear','figure','pn2','pn_q2')
BLOCKS = (('energy',slice(0,1)),('momentum',slice(1,4)),('angular',slice(4,7)))


def dec(x):
    return x if isinstance(x,Decimal) else Decimal.from_float(float(x))


def dot(a,b):
    return sum((x*y for x,y in zip(a,b)),ZERO)


def norm(a):
    return dot(a,a).sqrt()


def cross(a,b):
    return [a[(k+1)%3]*b[(k+2)%3]-a[(k+2)%3]*b[(k+1)%3] for k in range(3)]


def plus(*arrays):
    return [sum(row,ZERO) for row in zip(*arrays)]


def convert(state,masses,figures):
    q=np.asarray(state,dtype=float);m=np.asarray(masses,dtype=float)
    if m.ndim!=1 or not len(m) or q.shape!=(len(m),6) or not np.isfinite(q).all() or not np.isfinite(m).all() or not (m>0).all():
        raise ValueError('Invalid identity state or masses')
    fig=[]
    for i,r,tensor in figures:
        a=np.asarray(tensor,dtype=float)
        if not 0<=i<len(m) or not np.isfinite(r) or r<=0 or a.shape!=(3,3) or not np.isfinite(a).all():
            raise ValueError('Invalid identity figure')
        fig.append((i,dec(r),[[dec(x) for x in row] for row in a]))
    return ([[dec(x) for x in row[:3]] for row in q],[[dec(x) for x in row[3:]] for row in q],list(map(dec,m)),fig)


def pack(p,v,response):
    return [sum((dot(w,r) for w,r in zip(v,response)),ZERO),
        *plus(*response),*plus(*(cross(x,r) for x,r in zip(p,response)))]


def parts(p,v,m,fig,g,c):
    """Analytic F_N,F_PN,F_Q from EIH action; retain the static PN term."""
    c2=c*c;speed=[dot(w,w) for w in v]
    canonical_n=[[a*x for x in w] for a,w in zip(m,v)]
    canonical_pn=[[a*s*x/(2*c2) for x in w] for a,s,w in zip(m,speed,v)]
    energy_n=sum((a*s/2 for a,s in zip(m,speed)),ZERO)
    energy_pn=sum((3*a*s*s/(8*c2) for a,s in zip(m,speed)),ZERO)
    u=[ZERO]*len(m)
    for i in range(len(m)):
        for j in range(i+1,len(m)):
            r=[a-b for a,b in zip(p[i],p[j])];distance=norm(r)
            if not distance:raise ValueError('Coincident identity point masses')
            n=[x/distance for x in r];ni,nj=dot(n,v[i]),dot(n,v[j])
            factor=g*m[i]*m[j]/distance
            energy_n-=factor
            energy_pn+=factor*(3*(speed[i]+speed[j])-7*dot(v[i],v[j])-ni*nj)/(2*c2)
            u[i]+=g*m[j]/distance;u[j]+=g*m[i]/distance
            for k in range(3):
                canonical_pn[i][k]+=factor*(6*v[i][k]-7*v[j][k]-n[k]*nj)/(2*c2)
                canonical_pn[j][k]+=factor*(6*v[j][k]-7*v[i][k]-n[k]*ni)/(2*c2)
    static=sum((a*b*b/(2*c2) for a,b in zip(m,u)),ZERO)
    energy_pn+=static
    figure=ZERO
    for i,radius,q in fig:
        for j in range(len(m)):
            if i==j:continue
            r=[a-b for a,b in zip(p[j],p[i])];distance=norm(r)
            if distance<=radius:raise ValueError('Inside identity figure radius')
            qr=[dot(row,r) for row in q]
            figure+=g*m[i]*m[j]*dot(r,qr)/(2*distance**5)
    def vector(e,canonical):
        return [e,*plus(*canonical),*plus(*(cross(x,r) for x,r in zip(p,canonical)))]
    return dict(newton=vector(energy_n,canonical_n),pn=vector(energy_pn,canonical_pn),
        figure=[figure]+[ZERO]*6,static_pn=[static]+[ZERO]*6)


def forces(p,v,m,fig,g,c):
    """Independent scalar, full N-body order-reduced EIH and tensor J2."""
    count=len(m);mu=[g*x for x in m];u=[ZERO]*count
    nforce=[[ZERO]*3 for _ in m];pn=[[ZERO]*3 for _ in m];aq=[[ZERO]*3 for _ in m]
    geometry={}
    for i in range(count):
        for j in range(count):
            if i==j:continue
            d=[a-b for a,b in zip(p[j],p[i])];r=norm(d)
            if not r:raise ValueError('Coincident identity point masses')
            n=[x/r for x in d];geometry[i,j]=(d,r,n)
            u[i]+=mu[j]/r
            for k in range(3):nforce[i][k]+=mu[j]*d[k]/r**3
    speed=[dot(w,w) for w in v]
    for (i,j),(d,r,n) in geometry.items():
        bracket=speed[i]+2*speed[j]-4*dot(v[i],v[j])-3*dot(n,v[j])**2/2-4*u[i]-u[j]+dot(d,nforce[j])/2
        projection=dot(n,[4*a-3*b for a,b in zip(v[i],v[j])])
        for k in range(3):
            pn[i][k]+=(mu[j]/r**2*(n[k]*bracket-projection*(v[i][k]-v[j][k]))
                +Decimal('3.5')*mu[j]/r*nforce[j][k])/(c*c)
    for i,radius,q in fig:
        for j in range(count):
            if i==j:continue
            d,r,_=geometry[i,j]
            if r<=radius:raise ValueError('Inside identity figure radius')
            qr=[dot(row,d) for row in q];quadratic=dot(d,qr)
            for k in range(3):
                gradient=qr[k]/r**5-Decimal('2.5')*quadratic*d[k]/r**7
                aq[j][k]-=g*m[i]*gradient;aq[i][k]+=g*m[j]*gradient
    return nforce,pn,aq


def response(p,v,m,b,g,c):
    """Analytic Hessian of L_PN applied to a direction, kept per body."""
    result=[]
    for i in range(len(m)):
        row=[m[i]*(dot(v[i],v[i])*b[i][k]/2+v[i][k]*dot(v[i],b[i])) for k in range(3)]
        for j in range(len(m)):
            if i==j:continue
            d=[a-z for a,z in zip(p[i],p[j])];r=norm(d);n=[x/r for x in d]
            for k in range(3):row[k]+=g*m[i]*m[j]/(2*r)*(6*b[i][k]-7*b[j][k]-n[k]*dot(n,b[j]))
        result.append([x/(c*c) for x in row])
    return result


def direction(p,v,m,fig,g,c,kind,dp,dv,h):
    values=[]
    for sign in (-1,1):
        pp=[[x+sign*h*a for x,a in zip(row,d)] for row,d in zip(p,dp)]
        vv=[[x+sign*h*a for x,a in zip(row,d)] for row,d in zip(v,dv)]
        values.append(parts(pp,vv,m,fig,g,c)[kind])
    return [(b-a)/(2*h) for a,b in zip(*values)]


def strength(p,v,vectors):
    """Non-cancelled physical scales, with no epsilon or unitless floor."""
    sizes=[norm(row) for row in vectors]
    return [sum((norm(w)*s for w,s in zip(v,sizes)),ZERO),sum(sizes,ZERO),
        sum((norm(x)*s for x,s in zip(p,sizes)),ZERO)]


def score(actual,expected,scale,limit):
    result={}
    for i,(name,block) in enumerate(BLOCKS):
        error=norm([a-b for a,b in zip(actual[block],expected[block])]);signal=norm(expected[block])
        scaled=error/scale[i] if scale[i] else (ZERO if not error else None)
        relative=error/signal if signal else None
        result[name]=dict(scaled_error=float(scaled) if scaled is not None else None,
            relative_signal_error=float(relative) if relative is not None else None,signal_active=bool(signal),
            checks_passed=bool(scaled is not None and scaled<limit and (relative is None or relative<limit)))
    return dict(blocks=result,checks_passed=all(r['checks_passed'] for r in result.values()))


def snapshot(state,masses,figures,precision):
    if precision not in (70,90):raise ValueError('Undeclared identity precision')
    with localcontext() as context:
        context.prec=precision
        p,v,m,fig=convert(state,masses,figures);g,c=dec(G),dec(C)
        a_n,a_pn,a_q=forces(p,v,m,fig,g,c);zero=[[ZERO]*3 for _ in m]
        r2=response(p,v,m,a_pn,g,c);rq=response(p,v,m,a_q,g,c)
        qforces=[[mass*x for x in row] for mass,row in zip(m,a_q)]
        torque=pack(p,v,qforces)[4:]
        expected=dict(newton=[ZERO]*7,pn_linear=[ZERO]*7,figure=[ZERO]*4+torque,
            pn2=pack(p,v,r2),pn_q2=pack(p,v,rq))
        bounds=dict(newton=strength(p,v,[[mass*x for x in row] for mass,row in zip(m,a_n)]),
            pn_linear=strength(p,v,[[mass*x for x in row] for mass,row in zip(m,a_pn)]),
            figure=strength(p,v,qforces),pn2=strength(p,v,r2),pn_q2=strength(p,v,rq))
        pair_pn=[[ZERO]*3 for _ in m]
        for i in range(len(m)):
            for j in range(i+1,len(m)):
                _,two,_=forces([p[i],p[j]],[v[i],v[j]],[m[i],m[j]],[],g,c)
                pair_pn[i]=plus(pair_pn[i],two[0]);pair_pn[j]=plus(pair_pn[j],two[1])
        pair_change=pack(p,v,[[mass*(a-b) for a,b in zip(pa,full)] for mass,pa,full in zip(m,pair_pn,a_pn)])
        missing=[row.copy() for row in a_q]
        for i,_,_ in fig:missing[i]=[ZERO]*3
        reaction_change=pack(p,v,[[mass*(a-b) for a,b in zip(wrong,right)] for mass,wrong,right in zip(m,missing,a_q)])
        levels=[]
        for step in STEPS:
            h=Decimal(step)
            def d(kind,dp,dv):return direction(p,v,m,fig,g,c,kind,dp,dv,h)
            rates=dict(newton=plus(d('newton',v,zero),d('newton',zero,a_n)),
                pn_linear=plus(d('pn',v,zero),d('pn',zero,a_n),d('newton',zero,a_pn)),
                figure=plus(d('figure',v,zero),d('newton',zero,a_q)),
                pn2=d('pn',zero,a_pn),pn_q2=d('pn',zero,a_q))
            checks={key:score(rates[key],expected[key],bounds[key],Decimal('1e-8')) for key in CHANNELS}
            bad_static=plus(rates['pn_linear'],[-x for x in d('static_pn',v,zero)])
            bad_pair=plus(rates['pn_linear'],pair_change)
            bad_reaction=plus(rates['figure'],reaction_change)
            def defect(a,b,scale):
                return max((norm([x-y for x,y in zip(a[block],b[block])])/s if s else ZERO
                    for (_,block),s in zip(BLOCKS,scale)),default=ZERO)
            controls=dict(missing_reaction_defect=float(defect(bad_reaction,expected['figure'],bounds['figure'])),
                missing_static_energy_defect=float(abs(bad_static[0])/bounds['pn_linear'][0]) if bounds['pn_linear'][0] else 0.,
                pair_only_pn_defect=float(defect(bad_pair,expected['pn_linear'],bounds['pn_linear'])),
                omitted_sources={key:{name:float(norm(rates[key][block])/norm(expected[key][block]))
                    if norm(expected[key][block]) else None for name,block in BLOCKS} for key in ('pn2','pn_q2')})
            levels.append(dict(h_seconds=step,rates={k:list(map(str,r)) for k,r in rates.items()},checks=checks,negative_controls=controls))
        last,previous=levels[-1],levels[-2]
        refinement={key:score(list(map(Decimal,last['rates'][key])),list(map(Decimal,previous['rates'][key])),
            bounds[key],Decimal('1e-8')) if key in ('pn2','pn_q2') else score(
                plus(list(map(Decimal,last['rates'][key])),[-x for x in map(Decimal,previous['rates'][key])]),
                [ZERO]*7,bounds[key],Decimal('1e-8')) for key in CHANNELS}
        return dict(precision=precision,levels=levels,derivative_refinement=refinement,
            expected={k:list(map(str,r)) for k,r in expected.items()},scales={k:list(map(str,r)) for k,r in bounds.items()},
            checks_passed=bool(all(r['checks_passed'] for r in last['checks'].values())
                and all(r['checks_passed'] for r in refinement.values())))


def precision_agreement(low,high):
    with localcontext() as context:
        context.prec=100
        result={}
        for key in CHANNELS:
            a=list(map(Decimal,low['levels'][-1]['rates'][key]));b=list(map(Decimal,high['levels'][-1]['rates'][key]))
            scale=list(map(Decimal,high['scales'][key]));expected=list(map(Decimal,high['expected'][key]))
            difference=plus(a,[-x for x in b])
            result[key]=score(difference,[ZERO]*7,scale,Decimal('1e-30'))
            for name,block in BLOCKS:
                signal=norm(expected[block])
                if signal:
                    relative=norm(difference[block])/signal
                    result[key]['blocks'][name]['relative_signal_error']=float(relative)
                    result[key]['blocks'][name]['checks_passed'] &= bool(relative<Decimal('1e-30'))
            result[key]['checks_passed']=all(r['checks_passed'] for r in result[key]['blocks'].values())
        return dict(channels=result,checks_passed=all(r['checks_passed'] for r in result.values()))
