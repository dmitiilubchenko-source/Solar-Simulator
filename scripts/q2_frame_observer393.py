"""High-precision saved-state observer for Newton M-Q only; never integrates."""
import math
from decimal import Decimal,localcontext


def _precision(value):
    if type(value) is not int or not 50<=value<=300:raise ValueError('Observer precision must be an integer50..300')
    return value


def number(value):
    if type(value) not in (int,float):raise ValueError('Expected finite builtin real scalar, excluding bool')
    try:x=float(value)
    except OverflowError as error:raise ValueError('Nonfinite number') from error
    if not math.isfinite(x):raise ValueError('Nonfinite number')
    return Decimal.from_float(x)


def vector(values,size):
    if type(values) not in (list,tuple) or len(values)!=size:raise ValueError('Invalid vector shape')
    return [number(x) for x in values]


def norm(values):return sum(x*x for x in values).sqrt()
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def orientation_angle(qa,qb,precision=80):
    """2 atan2(|vector(conj(qa)*qb)|,|scalar|); no trace/acos/subtraction1."""
    with localcontext() as ctx:
        ctx.prec=_precision(precision);a=vector(qa,4);b=vector(qb,4)
        na=norm(a);nb=norm(b)
        if not na or not nb:raise ValueError('Zero quaternion')
        c=cross(a[1:],b[1:]);v=[a[0]*b[i+1]-b[0]*a[i+1]-c[i] for i in range(3)]
        w=sum(x*y for x,y in zip(a,b))
        scale=na*nb
        return 2*math.atan2(float(norm(v)/scale),abs(float(w/scale)))


def rotation(q):
    w,x,y,z=vector(q,4);n=w*w+x*x+y*y+z*z
    if not n:raise ValueError('Zero quaternion')
    return [[1-2*(y*y+z*z)/n,2*(x*y-w*z)/n,2*(x*z+w*y)/n],
        [2*(x*y+w*z)/n,1-2*(x*x+z*z)/n,2*(y*z-w*x)/n],
        [2*(x*z-w*y)/n,2*(y*z+w*x)/n,1-2*(x*x+y*y)/n]]


def invariants(state,document,G,precision=80):
    """Principal-I scalar Hamiltonian, inertial orbital+spin L and total P.

    Returns Decimal strings; comparisons must subtract them before conversion
    to float. Agreement is about this truncated model, not nature or an IVP bound.
    """
    with localcontext() as ctx:
        ctx.prec=_precision(precision);g=number(G)
        if g<=0:raise ValueError('G must be positive')
        settings=document['settings']
        if settings['physics']!='newtonian' or settings.get('figures'):raise ValueError('Only Newton dynamic M-Q supported')
        bodies=document['bodies'];rot=document['rotations'];names=[b['name'] for b in bodies]
        if not bodies or len(set(names))!=len(names):raise ValueError('Invalid body identifiers')
        mass=[number(b['mass']) for b in bodies]
        if any(m<=0 for m in mass):raise ValueError('Invalid mass')
        if any(number(b.get('radius',0))!=0 or any(vector(b.get('spin',[0,0,0]),3)) for b in bodies):raise ValueError('Contact/passive spin unsupported')
        fields={}
        for name,count,size in [('positions',len(bodies),3),('velocities',len(bodies),3),('quaternions',len(rot),4),('spins',len(rot),3)]:
            values=state[name]
            if type(values) not in (list,tuple) or len(values)!=count:raise ValueError('Invalid state count')
            fields[name]=[vector(x,size) for x in values]
        p=fields['positions'];v=fields['velocities'];S=fields['spins'];q=fields['quaternions']
        E=sum(m*sum(t*t for t in u)/2 for m,u in zip(mass,v));P=[sum(m*u[k] for m,u in zip(mass,v)) for k in range(3)];L=[Decimal(0)]*3
        for m,x,u in zip(mass,p,v):L=[a+b for a,b in zip(L,cross(x,[m*t for t in u]))]
        for i in range(len(mass)):
            for j in range(i+1,len(mass)):
                d=norm([b-a for a,b in zip(p[i],p[j])])
                if not d:raise ValueError('Coincident bodies')
                E-=g*mass[i]*mass[j]/d
        seen=set();qnorm=[]
        for r,qq,s in zip(rot,q,S):
            if r['body'] not in names or r['body'] in seen:raise ValueError('Invalid rotation identifier')
            seen.add(r['body']);source=names.index(r['body']);figure=r['figure'];I=vector(figure['moments'],3)
            if any(t<=0 for t in I) or number(figure['mass'])!=mass[source]:raise ValueError('Invalid inertia/mass')
            R=rotation([float(t) for t in qq]);bodyS=[sum(R[k][j]*s[k] for k in range(3)) for j in range(3)]
            E+=sum(t*t/i for t,i in zip(bodyS,I))/2;L=[a+b for a,b in zip(L,s)];qnorm.append(str(norm(qq)-1))
            for j in range(len(mass)):
                if j==source:continue
                delta=[b-a for a,b in zip(p[source],p[j])];d=norm(delta);n=[t/d for t in delta]
                bodyN=[sum(R[k][u]*n[k] for k in range(3)) for u in range(3)]
                E+=g*mass[j]*(3*sum(i*t*t for i,t in zip(I,bodyN))-sum(I))/(2*d**3)
        return dict(E_J=str(E),P_kg_m_s=[str(x) for x in P],L_kg_m2_s=[str(x) for x in L],qnorm_minus1=qnorm)


def differences(a,b,document,G,precision=80):
    """Euclidean per-body/pair differences and independent E/P/L differences."""
    with localcontext() as ctx:
        ctx.prec=_precision(precision);ia=invariants(a,document,G,precision);ib=invariants(b,document,G,precision)
        if len(document['bodies'])<2:raise ValueError('Pair comparison needs at least two bodies')
        gap=lambda x,y:float(norm([number(u)-number(v) for u,v in zip(x,y)]))
        result={key:[gap(x,y) for x,y in zip(a[key],b[key])] for key in ['positions','velocities','spins']}
        result['raw_quaternion']=[gap(x,y) for x,y in zip(a['quaternions'],b['quaternions'])]
        aligned=[]
        for x,y in zip(a['quaternions'],b['quaternions']):
            xx=vector(x,4);yy=vector(y,4)
            if sum(u*v for u,v in zip(xx,yy))<0:yy=[-v for v in yy]
            aligned.append(float(norm([u-v for u,v in zip(xx,yy)])))
        result['sign_aligned_raw_quaternion']=aligned
        result['orientation_angle_rad']=[orientation_angle(x,y,precision) for x,y in zip(a['quaternions'],b['quaternions'])]
        for key in ['positions','velocities']:
            aa=[[number(t) for t in x] for x in a[key]];bb=[[number(t) for t in x] for x in b[key]]
            ra=[y-x for x,y in zip(aa[0],aa[1])];rb=[y-x for x,y in zip(bb[0],bb[1])]
            result['relative_'+key]=float(norm([x-y for x,y in zip(ra,rb)]))
            result['relative_'+key+'_norm_difference']=float(norm(ra)-norm(rb))
        result['E_difference_J']=float(Decimal(ia['E_J'])-Decimal(ib['E_J']))
        for field in ['P_kg_m_s','L_kg_m2_s']:
            result[field+'_difference']=[float(Decimal(x)-Decimal(y)) for x,y in zip(ia[field],ib[field])]
        return result
