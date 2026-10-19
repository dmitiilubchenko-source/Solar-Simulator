"""Independent T_n/T'_n/T''_n recurrence on fixed binary64 input coefficients."""
from decimal import Decimal, localcontext

import numpy as np

from scripts.de441_reader import EPOCH, DAY, SLOTS


def dec(value):
    return Decimal.from_float(float(value))


def recurrence(coefficients, x, span):
    t0, t1 = Decimal(1), x
    d0, d1 = Decimal(0), Decimal(1)
    a0, a1 = Decimal(0), Decimal(0)
    out = [dec(coefficients[0]), Decimal(0), Decimal(0)]
    if len(coefficients) > 1:
        out[0] += dec(coefficients[1])*t1
        out[1] += dec(coefficients[1])
    for coefficient in coefficients[2:]:
        t = 2*x*t1-t0
        d = 2*t1+2*x*d1-d0
        a = 4*d1+2*x*a1-a0
        for order, value in enumerate((t, d, a)):
            out[order] += dec(coefficient)*value
        t0, t1, d0, d1, a0, a1 = t1, t, d1, d, a1, a
    return [value*(2/span)**order for order, value in enumerate(out)]


def snapshot(reader, seconds, precision):
    if precision not in (70, 90):
        raise ValueError('Use predeclared70/90 precision')
    reader.locate(0, seconds)  # Domain guard only; selection below is independent.
    with localcontext() as context:
        context.prec = precision
        time = dec(seconds)
        for index, row in enumerate(reader.records):
            start = (dec(row[0])-dec(EPOCH))*dec(DAY)
            end = (dec(row[1])-dec(EPOCH))*dec(DAY)
            if start <= time < end or index == len(reader.records)-1 and time == end:
                break
        native = []
        for slot in SLOTS:
            offset, count, parts = map(int, reader.layout[:, slot])
            span = dec(32*DAY)/parts
            sub = min(int((time-start)//span), parts-1)
            x = 2*(time-start-sub*span)/span-1
            first = offset-1+sub*3*count
            coefficients = reader.records[index, first:first+3*count].reshape(3, count)
            native.append(np.array([recurrence(c, x, span) for c in coefficients], dtype=object).T)
        native = np.array(native, dtype=object)
        relative = native[4].copy()
        native[3] -= relative/(1+dec(reader.constants['EMRAT']))
        native[4] = native[3]+relative
        frame = np.array([[dec(v) for v in row] for row in reader.frame], dtype=object)
        barycentric = np.array([[[sum(frame[j, k]*native[i, order, k] for k in range(3))*1000
            for j in range(3)] for i in range(10)] for order in range(3)], dtype=object)
        pair = np.array([[sum(frame[j, k]*relative[order, k] for k in range(3))*1000
            for j in range(3)] for order in range(3)], dtype=object)
        return barycentric, pair


def difference(actual, expected):
    actual = np.asarray(actual, dtype=object)
    with localcontext() as context:
        context.prec = 90
        return np.array([float(sum((dec(x)-y)**2 for x, y in zip(a, b)).sqrt())
            for a, b in zip(actual.reshape(-1, 3), expected.reshape(-1, 3))]).reshape(actual.shape[:-1])


def agreement(first, second):
    with localcontext() as context:
        context.prec = 90
        return float(max(abs(a-b)/max(Decimal(1), abs(b)) for a, b in zip(first.flat, second.flat)))
