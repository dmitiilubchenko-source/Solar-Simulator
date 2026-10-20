"""Bounded Decimal relative two-body diagnostic on the frozen337 step grid."""
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import json
import math

from scripts.assess_rust_trace import bits, coefficients


def relative_rhs(state,mu):
    """Same relative Newton equation as161, without float input/output casts."""
    if (len(state)!=6 or not isinstance(mu,D) or not mu.is_finite() or mu<=0
            or any(not isinstance(x,D) or not x.is_finite() for x in state)):
        raise ValueError('Expected six finite Decimal values and positive mu')
    radius=sum((x*x for x in state[:3]),D(0)).sqrt()
    if radius==0:
        raise ValueError('Singular relative state')
    return tuple(state[3:])+tuple(-mu*x/radius**3 for x in state[:3])


def rk_step(state,h,a,b,rhs):
    """The existing twelve-stage tableau; fixed positive h, no error controller."""
    if (not isinstance(h,D) or not h.is_finite() or h<=0 or len(state)!=6
            or len(a)!=12 or any(len(row)!=12 for row in a) or len(b)!=12):
        raise ValueError('Invalid fixed-step input')
    k=[rhs(state)]
    for s in range(1,12):
        trial=tuple(state[i]+h*sum((a[s][j]*k[j][i] for j in range(s)),D(0))
                    for i in range(6))
        k.append(rhs(trial))
    result=tuple(state[i]+h*sum((b[j]*k[j][i] for j in range(12)),D(0)) for i in range(6))
    if any(not x.is_finite() for x in result):
        raise ArithmeticError('Nonfinite shadow state')
    return result


def trace_grid(path,endpoints,statistics):
    """Check chronology/footer again;337's pinned SHA binds its full replay audit."""
    with path.open(encoding='utf-8') as stream:
        header=json.loads(next(stream))
        if header.get('kind')!='header' or header.get('schema')!=337:
            raise ValueError('Invalid337 trace header')
        ordered=[x for row in header['a'] for x in row]+header['b']+header['c']+header['e3']+header['e5']
        if b''.join(map(bits,ordered))!=coefficients():
            raise ValueError('Trace table changed')
        steps=[]; initial=current=None; time=0.; packet=accepted=rejected=0; footer=None
        for line in stream:
            row=json.loads(line)
            if row.get('kind')=='finish':
                footer=row
                if stream.read(): raise ValueError('Data after trace finish')
                break
            if (row.get('kind')!='attempt' or packet>=len(endpoints)
                    or row['time']!=time or row['packet_end']!=endpoints[packet]
                    or not time<row['next']<=row['packet_end'] or row['h']!=row['next']-time
                    or not math.isfinite(row['h']) or not math.isfinite(row['error']) or row['error']<0
                    or type(row['accepted']) is not bool or row['accepted']!=(row['error']<1.)):
                raise ValueError('Invalid337 trace chronology/acceptance')
            for key in ('old','trial'):
                if len(row[key])!=12 or not all(math.isfinite(x) for x in row[key]):
                    raise ValueError('Invalid337 trace state')
            old=b''.join(map(bits,row['old']))
            if current is not None and old!=current:
                raise ValueError('Uncommitted trace state change')
            current=old
            if initial is None:
                initial=tuple(D.from_float(x) for x in row['old'][3:6]+row['old'][9:12])
            if row['accepted']:
                steps.append((row['next'],row['h']))
                current=b''.join(map(bits,row['trial']));time=row['next'];accepted+=1
                if time==row['packet_end']: packet+=1
            else: rejected+=1
        if (initial is None or footer is None or footer.get('statistics')!=statistics
                or accepted!=statistics['accepted'] or rejected!=statistics['rejected']
                or packet!=len(endpoints)):
            raise ValueError('Incomplete337 trace')
    return header,initial,steps


def exact_elapsed(value):
    with localcontext() as context:
        context.prec=110
        result=D(value.numerator)/D(value.denominator)
        if F(result)!=value:
            raise ArithmeticError('Exact elapsed time exceeds diagnostic Decimal capacity')
        return result


def trajectory(initial,steps,times,header,mu,precision):
    if (precision not in (50,80) or len(times)<2 or times[0]!=0
            or any(not math.isfinite(float(t)) for t in times)
            or any(b<=a for a,b in zip(times,times[1:]))):
        raise ValueError('Expected frozen forward epochs and precision50/80')
    wanted=set(map(float,times[1:]));values=[tuple(initial)];elapsed=[D(0)]
    state=tuple(initial);clock=F(0);previous=0.
    with localcontext() as context:
        context.prec=precision
        a=tuple(tuple(D.from_float(x) for x in row) for row in header['a'])
        b=tuple(D.from_float(x) for x in header['b'])
        for next_time,h in steps:
            if not previous<next_time or h!=next_time-previous:
                raise ValueError('Changed fixed grid')
            state=rk_step(state,D.from_float(h),a,b,lambda y:relative_rhs(y,mu))
            clock+=F(h);previous=next_time
            if next_time in wanted:
                values.append(state);elapsed.append(exact_elapsed(clock))
    if len(values)!=len(times) or previous!=times[-1]:
        raise ValueError('Frozen grid misses an output epoch')
    return values,elapsed


def invariant_drifts(values,mu):
    with localcontext() as context:
        context.prec=110
        def row(y):
            p,v=y[:3],y[3:]
            energy=sum(x*x for x in v)/2-mu/sum(x*x for x in p).sqrt()
            angular=tuple(p[(i+1)%3]*v[(i+2)%3]-p[(i+2)%3]*v[(i+1)%3] for i in range(3))
            return energy,angular
        energy0,angular0=row(values[0]);scale=sum(x*x for x in angular0).sqrt()
        if energy0==0 or scale==0: raise ValueError('Degenerate shadow invariants')
        energy_drift=angular_drift=D(0)
        for y in values:
            energy,angular=row(y)
            energy_drift=max(energy_drift,abs((energy-energy0)/energy0))
            angular_drift=max(angular_drift,sum((a-b)**2 for a,b in zip(angular,angular0)).sqrt()/scale)
        return dict(relative_specific_energy_drift=float(energy_drift),relative_angular_drift=float(angular_drift))
