from dataclasses import replace
from math import sqrt,pi
from pathlib import Path

import numpy as np
import pytest

from scripts.ias15_reference import load_library,ias_trajectory,dop_trajectory,packet_end,validate_input
from solar_simulator.experiment import Settings,create_experiment
from solar_simulator.simulation import Body,G
from solar_simulator.vector3 import Vector3


@pytest.fixture
def library():
    directory=Path(__file__).resolve().parents[1]/'.tools/ias15165/dependency'
    if directory.is_dir():
        return load_library(directory)
    pytest.importorskip('rebound',reason='Optional isolated IAS15 research package is absent')
    return load_library()


def circle():
    mass,radius=1e20,1e7
    omega=sqrt(2*G*mass/radius**3);period=2*pi/omega
    seed=create_experiment([
        Body('A',mass,Vector3(-radius/2,0.,0.),Vector3(0.,0.,-radius*omega/2)),
        Body('B',mass,Vector3(radius/2,0.,0.),Vector3(0.,0.,radius*omega/2))],
        Settings(period/50,backend='rust',integrator='dop853',relative_pair=('A','B'),
                 rtol=3e-14,position_atol=1e-7,velocity_atol=1e-13))
    return seed,np.array([0.,period/4,period/2,period,2*period]),radius,omega


@pytest.mark.parametrize('epsilon',[1e-9,1e-11])
def test_equal_mass_3d_circle_against_independent_quarter_orbit_targets(library,epsilon):
    seed,times,radius,omega=circle()
    actual,stats=ias_trajectory(seed,times,library,epsilon)
    relative=actual[:,1]-actual[:,0]
    for state,time in zip(relative,times):
        expected_p=radius*np.array([np.cos(omega*time),0.,np.sin(omega*time)])
        expected_v=radius*omega*np.array([-np.sin(omega*time),0.,np.cos(omega*time)])
        assert np.linalg.norm(state[:3]-expected_p)<1e-3
        assert np.linalg.norm(state[3:]-expected_v)<1e-8
    np.testing.assert_array_equal(actual[0],np.array([[b.position.x,b.position.y,b.position.z,
        b.velocity.x,b.velocity.y,b.velocity.z] for b in seed.bodies]))
    assert stats['packet_endpoints'][-1]==times[-1]


def test_callback_counter_does_not_change_trajectory_and_packet_grid_matches_dop(library):
    seed,times,_,_=circle()
    original,stats=ias_trajectory(seed,times,library,1e-9)
    counted,count_stats=ias_trajectory(seed,times,library,1e-9,count_forces=True)
    repeat,_=ias_trajectory(seed,times,library,1e-9)
    _,dop=dop_trajectory(seed,times)
    np.testing.assert_array_equal(original,counted)
    np.testing.assert_array_equal(original,repeat)
    assert stats['packet_endpoints']==dop['packet_endpoints']
    assert count_stats['force_evaluations']>count_stats['steps_done']>0


@pytest.mark.parametrize('field,value',[('physics','eih-1pn')])
def test_research_rejects_an_unsupported_physical_model(field,value):
    seed,times,_,_=circle()
    seed=replace(seed,settings=replace(seed.settings,**{field:value}))
    with pytest.raises(ValueError,match='two Newtonian'):
        validate_input(seed,times)


@pytest.mark.parametrize('times',[[0.,0.,1.],[1.,2.],[0.,float('nan')],[0.,-1.]])
def test_research_rejects_invalid_epoch_grids(times):
    seed,_,_,_=circle()
    with pytest.raises(ValueError,match='epoch grid'):
        validate_input(seed,times)


def test_packet_endpoint_preserves_fractional_limit_and_rejects_no_progress():
    assert packet_end(3.,3.125,10.)==3.125
    with pytest.raises(ValueError,match='advance'):
        packet_end(1e20,1e20+1e6,1.)


def test_missing_explicit_library_is_not_silently_replaced(tmp_path):
    with pytest.raises(ValueError,match='does not contain'):
        load_library(tmp_path)
