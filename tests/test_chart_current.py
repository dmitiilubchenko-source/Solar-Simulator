import numpy as np
import pytest

from scripts import chart_current as current


def data():
    m=np.array([1.,2.,3.]);x=np.array([[0.,0.,0.],[.2,.3,.4],[-.5,.1,.2]])
    v=np.array([[.1,.2,.3],[-.2,.1,.3],[.4,-.1,.2]]);p=np.array([[1.,2.,3.],[2.,-1.,.5],[-1.,2.,3.]])
    return m,x,v,p


def test_nonlinear_radial_cotangent_work_axial_charge_and_metric_quadratic_form():
    m,x,v,p=data();rsq=np.sum(x*x,axis=1);a=.8;b=.12;tangent=a+b*rsq;radial=a+3*b*rsq
    result=current.snapshot(m,x,v,p,radial,tangent,1+.2*rsq,.9)
    assert np.max(abs(result['areal_pairing_kg_m2_s2']-result['mapped_pairing_kg_m2_s2']))<8e-16
    assert np.max(abs(result['areal_axial_charge_kg_m2_s']-result['mapped_axial_charge_kg_m2_s']))<8e-16
    assert abs(result['areal_quadratic_kinetic_j']-result['mapped_quadratic_kinetic_j'])<2e-16
    # Independently differentiate the actual position map by complex steps.
    for i,point in enumerate(x):
        for axis in range(3):
            z=point.astype(complex);z[axis]+=1j*1e-20;mapped=(a+b*np.sum(z*z))*z
            assert np.max(abs(mapped.imag/1e-20-result['jacobians'][i,:,axis]))<2e-16
    assert np.max(abs(result['mapped_positions_m']-np.einsum('nij,nj->ni',result['jacobians'],x)))>.001


def test_affine_limit_coordinate_second_moments_and_no_recentering():
    m,x,v,p=data();result=current.snapshot(m,x,v,p,.8,.8,1.,1.)
    assert np.max(abs(result['mapped_second_moment_kg_m2']-.8**2*result['areal_second_moment_kg_m2']))<3e-16
    assert np.linalg.norm(result['areal_first_moment_kg_m'])>0.
    assert np.max(abs(result['mapped_first_moment_kg_m']-.8*result['areal_first_moment_kg_m']))<3e-16


def test_density_is_a_weight_and_uses_inverse_determinant():
    density=np.array([0.,2.,3.]);det=np.array([.5,2.,3.])
    mapped=current.current_density_pullback(density,det)
    assert np.array_equal(mapped*det,density)
    with pytest.raises(ValueError):current.current_density_pullback([-1.,2.,3.],det)


@pytest.mark.parametrize('bad',[0.,-1.,float('nan'),True,1j,[1.,2.]])
def test_invalid_differential_fields_rejected(bad):
    with pytest.raises(ValueError):current.snapshot(*data(),bad,1.,1.,1.)


def test_irregular_origin_and_extreme_conditioning_rejected():
    with pytest.raises(ValueError,match='centre'):current.snapshot(*data(),.8,.9,1.,1.)
    with pytest.raises(ValueError,match='condition'):current.snapshot(*data(),1.,[1.,1e-10,1e-10],1.,1.)
