import pytest
from scripts.q2_noether_observer395 import eih_noether_observer


def test_lagrangian_observer_has_analytic_free_particle_energy_and_canonical_momentum():
    g=6.6743e-11;c=299792458.;p=[[1.,2.,3.]];v=[[1e5,2e5,-3e5]];mass=5.
    out=eih_noether_observer(p,v,[mass],g,c);speed2=sum(x*x for x in v[0])
    momentum=[mass*x*(1+.5*speed2/c**2) for x in v[0]]
    assert out['E_J']==pytest.approx(mass*speed2/2+3*mass*speed2**2/(8*c**2),rel=2e-15)
    assert out['P_kg_m_s']==pytest.approx(momentum,rel=2e-15)
    assert out['L_kg_m2_s']==pytest.approx([p[0][1]*momentum[2]-p[0][2]*momentum[1],p[0][2]*momentum[0]-p[0][0]*momentum[2],p[0][0]*momentum[1]-p[0][1]*momentum[0]],rel=2e-15)


@pytest.mark.parametrize('bad',[True,float('nan'),float('inf'),0.,-1.])
def test_invalid_mass_is_rejected(bad):
    with pytest.raises(ValueError):eih_noether_observer([[0.,0.,0.]],[[0.,0.,0.]],[bad],6.6743e-11,299792458.)


def test_two_static_points_newton_limit_and_inputs_are_preserved():
    p=[[0.,0.,0.],[10.,0.,0.]];v=[[0.,0.,0.],[0.,0.,0.]]
    assert eih_noether_observer(p,v,[2.,3.],1.,1e10)['E_J']==pytest.approx(-.6)
    assert p==[[0.,0.,0.],[10.,0.,0.]]
