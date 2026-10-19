"""Independent Decimal power-basis oracle of the pinned DE441 polynomials."""
from bisect import bisect_left, bisect_right
from decimal import Decimal, localcontext

import numpy as np

from scripts import de441_reader as de


def decimal(value):
    return value if isinstance(value, Decimal) else Decimal.from_float(float(value))


def power_basis(coefficients):
    """T recurrence in coefficient space; no Chebyshev evaluation/derivatives."""
    values = tuple(map(decimal, coefficients))
    if not values or not all(v.is_finite() for v in values):
        raise ValueError('Finite nonempty polynomial required')
    out = [Decimal(0)]*len(values)
    previous, current = [Decimal(1)], [Decimal(0), Decimal(1)]
    for n, coefficient in enumerate(values):
        if n == 0: polynomial = previous
        elif n == 1: polynomial = current
        else:
            polynomial = [Decimal(0)]*(n+1)
            for i,v in enumerate(current):polynomial[i+1] += 2*v
            for i,v in enumerate(previous):polynomial[i] -= v
            previous,current = current,polynomial
        for i,v in enumerate(polynomial):out[i] += coefficient*v
    return tuple(out)


def derivative(coefficients, order):
    if type(order) is not int or order not in (0,1,2):
        raise ValueError('Derivative order0/1/2 required')
    values = tuple(coefficients)
    for _ in range(order):
        values = tuple(i*values[i] for i in range(1,len(values))) or (Decimal(0),)
    return values


def horner(coefficients, x):
    result = Decimal(0)
    for value in reversed(coefficients):result = result*x+value
    return result


def choose(starts, ends, seconds, side):
    if side not in ('left','right'):
        raise ValueError('Explicit left/right polynomial side required')
    i = (bisect_left(starts, seconds) if side == 'left' else bisect_right(starts, seconds))-1
    if i < 0 or not starts[i] <= seconds <= ends[i]:
        raise ValueError('Time outside available polynomial blocks')
    return i


class Oracle:
    def __init__(self, reader, raw, precision, binary64):
        if precision not in (70,90) or type(binary64) is not bool:
            raise ValueError('Predeclared precision70/90 and explicit coefficient representation required')
        self.reader,self.precision,self.binary64 = reader,precision,binary64
        tokens = raw.decode('ascii').replace('D','E').split()
        if len(tokens) != len(reader.records)*1020:
            raise ValueError('ASCII record inventory differs')
        self.rows = [tokens[k+2:k+1020] for k in range(0,len(tokens),1020)]
        if not np.array_equal(np.array(self.rows,dtype=float),reader.records):
            raise ValueError('Source tokens and loaded binary64 coefficients differ')
        self.blocks,self.starts,self.ends,self.cache = {},{},{},{}
        for slot in de.SLOTS:
            blocks=[];parts=int(reader.layout[2,slot]);span=Decimal(32*86400)/parts
            for record,row in enumerate(self.rows):
                start=(Decimal(row[0])-Decimal(str(de.EPOCH)))*86400
                for segment in range(parts):blocks.append((start+segment*span,span,record,segment))
            self.blocks[slot]=blocks
            self.starts[slot]=[v[0] for v in blocks]
            self.ends[slot]=[v[0]+v[1] for v in blocks]

    def polynomials(self, slot, index):
        key=(slot,index)
        if key not in self.cache:
            _,_,record,segment=self.blocks[slot][index]
            offset,count,_=map(int,self.reader.layout[:,slot])
            first=offset-1+segment*3*count
            rows=[self.rows[record][first+k*count:first+(k+1)*count] for k in range(3)]
            convert=(lambda v:decimal(float(v))) if self.binary64 else Decimal
            power=[power_basis(tuple(convert(v) for v in row)) for row in rows]
            self.cache[key]=[[derivative(c,order) for c in power] for order in range(3)]
        return self.cache[key]

    def evaluate(self, seconds, side='right', orders=(2,)):
        time=decimal(seconds)
        if (not time.is_finite() or not 0 <= time <= decimal(self.reader.duration)
                or not orders or any(type(o) is not int or o not in (0,1,2) for o in orders)):
            raise ValueError('Finite covered time and derivative orders required')
        with localcontext() as context:
            context.prec=self.precision
            native=[]
            for slot in de.SLOTS:
                index=choose(self.starts[slot],self.ends[slot],time,side)
                start,span,_,_=self.blocks[slot][index]
                x=2*(time-start)/span-1
                polys=self.polynomials(slot,index)
                native.append([[horner(c,x)*(2/span)**order for c in polys[order]] for order in orders])
            native=np.array(native,dtype=object)
            relative=native[4].copy()
            native[3] -= relative/(1+decimal(self.reader.constants['EMRAT']))
            native[4] = native[3]+relative
            frame=np.array([[decimal(v) for v in row] for row in self.reader.frame],dtype=object)
            result=[]
            for index in range(len(orders)):
                vectors=np.concatenate((native[:,index],relative[index:index+1]),axis=0)
                result.append([[sum(frame[j,k]*v[k] for k in range(3))*1000 for j in range(3)] for v in vectors])
            return np.array(result,dtype=object)

    def seams(self, end):
        return np.array(sorted({float(t) for starts in self.starts.values() for t in starts if 0<t<decimal(end)}))


def errors(actual, expected):
    """Subtract before float conversion; both absolute and own-vector norms."""
    a,b=np.asarray(actual,dtype=object),np.asarray(expected,dtype=object)
    if a.shape != b.shape or a.shape[-1:] != (3,):
        raise ValueError('Matching vectors required')
    absolute,relative=[],[]
    with localcontext() as context:
        context.prec=90
        for x,y in zip(a.reshape(-1,3),b.reshape(-1,3)):
            x,y=list(map(decimal,x)),list(map(decimal,y))
            if not all(v.is_finite() for v in x+y):raise ValueError('Finite vectors required')
            error=sum((u-v)**2 for u,v in zip(x,y)).sqrt();scale=sum(v*v for v in y).sqrt()
            if scale==0 and error!=0:raise ValueError('Nonzero difference against zero vector')
            absolute.append(float(error));relative.append(float(error/scale) if scale else 0.)
    shape=a.shape[:-1]
    return np.array(absolute).reshape(shape),np.array(relative).reshape(shape)


def split_difference(left, right, before, after):
    """D=J+S in SI acceleration vectors, with Decimal subtraction."""
    with localcontext() as context:
        context.prec=90
        jump=right-left
        smooth=(after-right)+(left-before)
        total=after-before
        identity=total-jump-smooth
        scale=np.maximum.reduce([np.linalg.norm(np.asarray(v,dtype=float),axis=-1) for v in (total,jump,smooth)])
        signal=np.linalg.norm(np.asarray(jump,dtype=float),axis=-1)
        missing=np.divide(signal,scale,out=np.zeros_like(signal),where=scale!=0)
        return jump,smooth,total,identity,missing
