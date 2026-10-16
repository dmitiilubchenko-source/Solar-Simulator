from dataclasses import replace
from decimal import localcontext

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_kepler_phase import fixture,decimal_relative
from scripts.assess_sandbox_planets import states
from solar_simulator.vector3 import Vector3


def test_orbital_budget_detects_an_internal_error_hidden_by_centre_of_mass_energy():
    # Newtonian diagnostic stress, not a physical relativistic simulation.
    # A common boost makes inertial kinetic energy dominate the orbit budget.
    # Only a middle sample is perturbed; a final-only check would miss it.
    seed,_=fixture(0.)
    bodies=[replace(b,velocity=Vector3(b.velocity.x+1e7,b.velocity.y,b.velocity.z)) for b in seed.bodies]
    seed=replace(seed,bodies=bodies,initial=bodies)
    initial=states(bodies)
    values=np.array([initial,initial,initial])
    values[1,1,5]+=.001
    with localcontext() as context:
        context.prec=110
        relative=decimal_relative(initial)
        reference=(relative[:3],relative[3:])
    result=metrics(seed,np.array([0.,1.,2.]),values,[reference]*3)
    assert result['relative_energy_drift']<1e-12
    assert result['specific_orbital_energy_drift']>1e-9
    assert result['velocity_m_per_s']>.0009 and not result['checks_passed']
    np.testing.assert_array_equal(values[-1],values[0])
