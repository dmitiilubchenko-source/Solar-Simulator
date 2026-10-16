from decimal import Decimal as D, localcontext

import pytest

from scripts.kepler_reference import propagate

PI = D("3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068")


def test_decimal_circle_at_quadrants_and_signed_revolutions():
    # mu=r=v=1 exactly: period=2*pi, independent of production constants.
    p, v = (D(1), D(0), D(0)), (D(0), D(0), D(1))
    with localcontext() as context:
        context.prec = 110
        for multiple in (-8, -3, -1, 0, 1, 2, 3, 4, 8):
            index = multiple % 4
            expected_p = ((1,0,0),(0,0,1),(-1,0,0),(0,0,-1))[index]
            expected_v = ((0,0,1),(-1,0,0),(0,0,-1),(1,0,0))[index]
            actual = propagate(p, v, D(1), PI*multiple/2)
            for got, expected in zip(actual, (expected_p, expected_v)):
                assert max(abs(x-D(y)) for x,y in zip(got,expected)) < D('1e-60')
        assert propagate(p,v,D(1),D(0)) == (p,v)


def test_decimal_ellipse_reversal_energy_angular_and_precision():
    # Nonzero radial speed, generic 3D, all input scalars exactly represented.
    p = tuple(map(D, ('2','-1','3')))
    v = tuple(map(D, ('.1','.4','-.1')))
    mu, elapsed = D(3), D(47)
    with localcontext() as context:
        context.prec = 110
        def invariants(p,v):
            energy=sum(x*x for x in v)/2-mu/sum(x*x for x in p).sqrt()
            angular=tuple(p[(i+1)%3]*v[(i+2)%3]-p[(i+2)%3]*v[(i+1)%3] for i in range(3))
            return energy,angular
        initial_e, initial_l = invariants(p,v)
        low=propagate(p,v,mu,elapsed,precision=70)
        high=propagate(p,v,mu,elapsed,precision=100)
        back=propagate(*high,mu,-elapsed,precision=100)
        for actual,expected in ((low,high),(back,(p,v))):
            assert max(abs(a-b) for x,y in zip(actual,expected) for a,b in zip(x,y)) < D('1e-60')
        energy,angular=invariants(*high)
        assert abs(energy-initial_e)<D('1e-90')
        assert max(abs(a-b) for a,b in zip(angular,initial_l))<D('1e-90')


@pytest.mark.parametrize('eccentricity,minor,speed', [('.6','.8','2'),('.96','.28','7')])
def test_independent_elliptic_quadrature_and_apoapse(eccentricity,minor,speed):
    # a=mu=1, rational Pythagorean semiaxes: eccentric anomaly pi/2 has
    # M=pi/2-e, r=(-e,b,0), v=(-1,0,0). These exact targets are not obtained
    # by propagating another instance of the f/g oracle.
    with localcontext() as context:
        context.prec=110
        e,b,w=map(D,(eccentricity,minor,speed))
        p,v=(1-e,D(0),D(0)),(D(0),w,D(0))
        targets=((PI/2-e,(-e,b,D(0)),(D(-1),D(0),D(0))),
                 (PI,(-1-e,D(0),D(0)),(D(0),-1/w,D(0))))
        for time,expected_p,expected_v in targets:
            actual=propagate(p,v,D(1),time,precision=100)
            assert max(abs(x-y) for row,target in zip(actual,(expected_p,expected_v))
                       for x,y in zip(row,target))<D('1e-88')


@pytest.mark.parametrize('p,v,mu,t', [
    ((0,0,0),(0,1,0),1,0), ((1,0,0),(1,0,0),1,0),
    ((1,0,0),(0,2,0),1,0), ((1,0,0),(0,1,0),0,0),
    ((1,0,0),(0,1,0),1,33), ((1,0,0),(0,1,0),1,'NaN'),
])
def test_reference_rejects_outside_declared_scope(p,v,mu,t):
    with pytest.raises(ValueError):
        propagate(tuple(map(D,p)),tuple(map(D,v)),D(mu),D(t))
