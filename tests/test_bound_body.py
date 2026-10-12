import numpy as np
import pytest

from scripts import bound_body as model
from scripts import independent_bound_reference as reference


def fixture():
    masses = (2., 3., 4., 2.5)
    links = tuple((i, j, 3.+i+j, 1.4+.1*j) for i in range(4) for j in range(i+1, 4))
    pars = model.Parameters(masses, links, .4, .05)
    x = np.array([[1.2, .1, -.3], [-.4, 1.3, .2], [-.7, -.5, 1.1], [.3, -.8, -1.]])
    v = np.cross([.2, -.3, .4], x)+.08*x+np.array([[.1, -.05, 0.], [0., .02, -.1], [-.1, 0., .03], [.01, .02, .03]])
    return pars, np.r_[x.ravel(), (np.array(masses)[:, None]*v).ravel()]


def test_potential_gradient_all_pair_reactions_and_torque():
    pars, y = fixture(); x, p, m = model.unpack(y, pars)
    force, vg, ve, w = model.fields(x, pars)
    grad = reference.gradient(y, m, pars.links, pars.gravitational_constant)
    assert np.linalg.norm(force.ravel()+grad[:12])/np.linalg.norm(force) < 1e-11
    assert np.linalg.norm(grad[12:].reshape(4,3)-p/m[:,None]) < 1e-11
    assert abs(reference.hamiltonian(y,m,pars.links,.4)-model.diagnostics(y,pars)['energy']) < 1e-11
    assert np.linalg.norm(force.sum(axis=0))/np.linalg.norm(force) < 1e-11
    assert np.linalg.norm(np.cross(x,force).sum(axis=0))/np.linalg.norm(force) < 1e-11
    assert np.linalg.norm(w-x.T@force)/np.linalg.norm(w) < 1e-11
    assert np.linalg.norm(w-w.T) < 1e-11


def test_symmetries_global_charges_and_no_state_or_parameter_edits():
    pars, y = fixture(); old = y.tobytes(); out = model.diagnostics(y,pars)
    a = .61; b = -.37
    rz = np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1.]])
    ry = np.array([[np.cos(b),0,np.sin(b)],[0,1.,0],[-np.sin(b),0,np.cos(b)]])
    r = rz@ry; shift=np.array([3.,-2.,1.]); boost=np.array([.7,-.2,.3])
    x,p,m = model.unpack(y,pars)
    yy=np.r_[(x@r.T+shift).ravel(),(p@r.T+m[:,None]*boost).ravel()]
    transformed=model.diagnostics(yy,pars)
    assert np.linalg.norm(transformed['force']-out['force']@r.T) < 1e-11
    assert np.linalg.norm(transformed['spin']-r@out['spin']) < 1e-11
    assert np.linalg.norm(transformed['inertia']-r@out['inertia']@r.T) < 1e-11
    expected_energy=out['energy']+boost@(r@out['momentum'])+.5*sum(m)*(boost@boost)
    assert abs(transformed['energy']-expected_energy) < 1e-11
    assert y.tobytes()==old
    input_m=[2.,3.];input_links=[[0,1,4.,1.]]
    snapshot=model.Parameters(input_m,input_links,0.,.01);input_m[0]=100.;input_links[0][2]=100.
    assert snapshot.masses==(2.,3.) and snapshot.links==((0,1,4.,1.),)


def test_tensor_scalar_virial_and_elastic_energy_are_distinct():
    pars,y=fixture();o=model.diagnostics(y,pars)
    direct=.5*o['second_moment_ddot']
    expected=o['kinetic_tensor']+o['pair_virial']
    assert np.linalg.norm(direct-expected)/np.linalg.norm(expected)<1e-11
    assert abs(np.trace(direct)-2*o['internal_kinetic']-np.trace(o['pair_virial']))<1e-11
    no_links=model.Parameters(pars.masses,(),.4,.05)
    gravity=model.diagnostics(y,no_links)
    assert abs(np.trace(gravity['pair_virial'])-gravity['gravity'])<1e-11
    elastic_virial=np.trace(o['pair_virial']-gravity['pair_virial'])
    assert abs(elastic_virial-o['elastic'])/abs(elastic_virial)>1e-4


def test_tisserand_least_squares_split_and_deformation_not_rigid_rotation():
    pars,y=fixture();o=model.rotation_split(y,pars)
    assert np.linalg.norm(o['residual_spin'])/np.linalg.norm(o['spin'])<1e-11
    assert abs(o['internal_kinetic']-o['rotation_energy']-o['residual_energy'])/o['internal_kinetic']<1e-11
    w=o['omega'];hat=np.array([[0,-w[2],w[1]],[w[2],0,-w[0]],[-w[1],w[0],0]])
    assert np.linalg.norm(o['inertia_dot']-hat@o['inertia']+o['inertia']@hat)/np.linalg.norm(o['inertia_dot'])>1e-4
    for delta in ([.1,0.,0.],[0.,-.2,.1]):
        residual=o['relative_velocities']-np.cross(w+delta,o['relative_positions'])
        energy=.5*np.sum(np.array(pars.masses)[:,None]*residual**2)
        assert energy>o['residual_energy']


def test_rigid_snapshot_Cdot_and_exact_circular_equilateral():
    mass=2.;radius=2.;k=4.;g=.4;length=np.sqrt(3)*1.8
    angle=2*np.pi*np.arange(3)/3;x=np.c_[radius*np.cos(angle),radius*np.sin(angle),np.zeros(3)]
    omega=np.sqrt(g*mass/(np.sqrt(3)*radius**3)+3*k/mass*(1-length/(np.sqrt(3)*radius)))
    v=np.cross([0.,0.,omega],x);pars=model.Parameters((mass,)*3,((0,1,k,length),(0,2,k,length),(1,2,k,length)),g,.05)
    y=np.r_[x.ravel(),(mass*v).ravel()];o=model.rotation_split(y,pars)
    assert np.linalg.norm(o['force']/mass+omega**2*x)/np.linalg.norm(omega**2*x)<1e-11
    assert np.linalg.norm(o['omega']-[0.,0.,omega])<1e-11
    assert o['residual_energy']/o['internal_kinetic']<1e-11
    hat=np.array([[0.,-omega,0.],[omega,0.,0.],[0.,0.,0.]])
    assert np.linalg.norm(o['inertia_dot']-hat@o['inertia']+o['inertia']@hat)/np.linalg.norm(o['inertia'])<1e-11


@pytest.mark.parametrize('m,links,g,d',[((1.,),(),.4,.1),((1.,-2.),(),.4,.1),((1.,2.),(),-.1,.1),
    ((1.,2.),(),.4,0.),((1.,2.),((1,0,2.,1.),),.4,.1),((1.,2.),((0,1,0.,1.),),.4,.1),
    ((1.,2.),((0,1,2.,1.),(0,1,3.,1.)),.4,.1),((1.,2.),((0.,1,2.,1.),),.4,.1),
    ((1.,2.),(),True,.1),((1.,np.nan),(),.4,.1)])
def test_invalid_model_rejected(m,links,g,d):
    with pytest.raises(ValueError):model.Parameters(m,links,g,d)


def test_domain_singular_rotation_nonfinite_and_overflow_rejected():
    pars=model.Parameters((1.,1.),((0,1,1.,1.),),.4,.1)
    y=np.r_[[-1.,0.,0.,1.,0.,0.],np.zeros(6)]
    assert model.diagnostics(y,pars)['energy']>0
    with pytest.raises(ValueError,match='inertia'):model.rotation_split(y,pars)
    with pytest.raises(ValueError):model.fields(np.zeros((2,3)),pars)
    with pytest.raises(ValueError):model.rhs(0.,np.full(12,np.nan),pars)
    with pytest.raises(ValueError):model.rhs(np.nan,y,pars)
    with pytest.raises(ValueError):model.fields([[1e300,0,0],[-1e300,0,0]],pars)
