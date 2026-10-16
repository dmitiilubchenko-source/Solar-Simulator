import numpy as np

from scripts import independent_current_reference as reference


def test_independent_angular_current_mass_first_and_tensor_integrals():
    n,w=reference.angular_grid(12,24);q=np.array([[.1,.04,0.],[.04,-.03,0.],[0.,0.,-.07]]);b=np.array([.1,-.04,.06])
    shape=1+np.einsum('ni,ij,nj->n',n,q,n)+n@b
    assert abs(np.dot(w,shape)-4*np.pi)<8e-15
    assert np.max(abs(n.T@(w*shape)-4*np.pi*b/3))<3e-15
    second=np.einsum('n,ni,nj->ij',w*shape,n,n)
    assert np.max(abs(second-4*np.pi*(np.eye(3)/3+2*q/15)))<8e-15
    assert np.min(shape)>0.
