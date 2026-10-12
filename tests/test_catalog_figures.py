"""Large-system developer reference still agrees with scalar body-axis fields."""
import numpy as np
import pytest
from functools import partial
from solar_simulator.kuiper_ring import solar_system_ring
from solar_simulator.perturbers import solar_system_asteroids_catalog,solar_system_kuiper
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from solar_simulator.simulation import AU,G
from scripts.assess_relativity import YEAR
from scripts.assess_resolved_moon import states
from scripts.assess_orientation import independent_figure_acceleration
from scripts.independent_figure_vector import acceleration


@pytest.mark.parametrize('time',[0.,43200.,31557600.])
@pytest.mark.parametrize('pair_mode',['none','forward','reverse'])
@pytest.mark.parametrize('loader',[solar_system_asteroids_catalog,solar_system_kuiper,partial(solar_system_ring,144)])
def test_vectorized_reference_matches_scalar_body_axes_for_all_354(time,pair_mode,loader):
    bodies,origin=loader()
    figures=sun_earth_moon_quadrupoles(bodies,origin)
    q=states(bodies);p=q[:,:3]/AU;mu=np.array([G*b.mass*YEAR**2/AU**3 for b in bodies])
    names=[b.name for b in bodies]
    pair=None if pair_mode=='none' else (3,4,p[4]-p[3]) if pair_mode=='forward' else (4,3,p[3]-p[4])
    actual=acceleration(p,mu,figures,names,time,pair)
    expected=independent_figure_acceleration(p,mu,figures,names,time,pair)
    assert np.allclose(actual,expected,rtol=3e-13,atol=1e-25)
    scale=np.max(np.sum(np.abs(actual)*mu[:,None],axis=0))
    assert np.linalg.norm(np.sum(actual*mu[:,None],axis=0))<1e-14*scale


def test_reference_pair_uses_its_small_vector_even_when_absolute_difference_is_lost():
    from solar_simulator.oblateness import FixedJ2
    figures=(FixedJ2('A',.001,6e6,(0.,0.,1.)),)
    p=np.full((2,3),1e30);mu=np.array([1.,.001]);rho=np.array([.01,.02,-.03])
    actual=acceleration(p,mu,figures,['A','B'],0.,(0,1,rho))
    expected=independent_figure_acceleration(p,mu,figures,['A','B'],0.,(0,1,rho))
    assert np.allclose(actual,expected,rtol=1e-14,atol=1e-25)
    with pytest.raises(ValueError): acceleration(p,mu,figures,['A','B'],0.)
