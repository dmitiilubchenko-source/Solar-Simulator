"""Different coordinates recover analytic dynamics without a production force."""
import numpy as np
import pytest
from solar_simulator.simulation import AU,G,Body
from solar_simulator.vector3 import Vector3
from scripts.assess_relativity import YEAR
from scripts.assess_resolved_moon import states
from scripts.independent_anchored_reference import independent_reference


def no_figures(p,*args): return np.zeros_like(p)


def test_anchored_reference_preserves_free_motion_masses_and_observer_frame(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    bodies=[Body('Earth',1e24,Vector3(AU,0,0),Vector3(1,2,3)),
        Body('Moon',1e22,Vector3(AU+3e8,0,0),Vector3(1,3,3)),
        Body('Distant',1e20,Vector3(100*AU,70*AU,-20*AU),Vector3(-2000,1000,3000))]
    original=states(bodies);calls=[]
    def free(p,v,mu,c,pair):
        assert np.array_equal(mu,np.array([G*b.mass*YEAR**2/AU**3 for b in bodies]))
        assert np.allclose(v,original[:,3:]*YEAR/AU,rtol=0.,atol=1e-16)
        assert pair[:2]==(0,1) and np.linalg.norm(pair[2])>0
        calls.append(1)
        return np.zeros_like(p)
    times=np.array([0.,43200.,86400.])
    actual,convergence=independent_reference(bodies,(),times,levels=((1e-12,900.),(1e-13,450.)),
        cache_name='free',acceleration_function=free,figure_acceleration_function=no_figures)
    expected=np.broadcast_to(original,actual.shape).copy()
    expected[:,:,:3]+=times[:,None,None]*original[None,:,3:]
    assert calls and np.max(np.linalg.norm(actual[:,:,:3]-expected[:,:,:3],axis=2))<.005
    assert convergence['all_bodies']['maximum_position_metres']<.005
    assert np.array_equal(original,states(bodies))


def test_anchored_pair_follows_independent_circular_kepler_solution(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    masses=np.array([5.972e24,7.348e22]);fraction=masses[1]/masses.sum()
    radius=3.844e8;omega=np.sqrt(G*masses.sum()/radius**3)
    rho=np.array([radius,0.,0.]);velocity=np.array([0.,omega*radius,0.])
    center=np.array([AU,AU/3.,AU/10.])
    bodies=[Body('Earth',masses[0],Vector3(*(center-fraction*rho)),Vector3(*(-fraction*velocity))),
        Body('Moon',masses[1],Vector3(*(center+(1-fraction)*rho)),Vector3(*((1-fraction)*velocity)))]
    def newton(p,v,mu,c,pair):
        e,m,r=pair
        f=r/np.linalg.norm(r)**3
        a=np.empty_like(p);a[e]=mu[m]*f;a[m]=-mu[e]*f
        return a
    times=np.array([0.,86400.,7*86400.])
    actual,convergence=independent_reference(bodies,(),times,levels=((1e-12,900.),(1e-13,450.)),
        cache_name='kepler',acceleration_function=newton,figure_acceleration_function=no_figures)
    expected=radius*np.column_stack((np.cos(omega*times),np.sin(omega*times),np.zeros(len(times))))
    relative=actual[:,1,:3]-actual[:,0,:3]
    assert np.max(np.linalg.norm(relative-expected,axis=1))<.003
    assert convergence['moon_relative_to_earth']['maximum_position_metres']<.003


@pytest.mark.parametrize('grid',[[0.,0.],[1.,2.],[0.,float('nan')],[0.,-1.]])
def test_invalid_anchored_grid_fails_before_any_force_call(grid):
    bodies=[Body('Earth',1e24,Vector3(0,0,0),Vector3(0,0,0)),
        Body('Moon',1e22,Vector3(3e8,0,0),Vector3(0,1000,0))]
    with pytest.raises(ValueError):
        independent_reference(bodies,(),grid,levels=((1e-12,900.),(1e-13,450.)),cache_name='bad',
            acceleration_function=lambda *args:pytest.fail('Force must not be called'),figure_acceleration_function=no_figures)
