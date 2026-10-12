"""Independent derivatives, exact SO reaction, coordinate and retained-order checks."""
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

from scripts.pn_spin_model import Parameters, hamiltonian, rhs, invariants, exact_so, validate
from scripts.independent_pn_spin import full_hamiltonian, gradient
from solar_simulator.relativity import eih_acceleration
from solar_simulator.simulation import G


PARAMETERS = Parameters(.3, .7, float(np.sqrt(1e5)))
STATE = np.array([.8, 0., 0., 0., .21*np.sqrt(1.5), 0., .003, -.004, .002])


def test_reduced_hamiltonian_and_rhs_against_original_two_body_derivatives():
    rng = np.random.default_rng(55)
    for _ in range(16):
        state = np.r_[rng.normal(size=3), rng.normal(size=3)*.05, rng.normal(size=3)*.003]
        validate(state, PARAMETERS)
        original = full_hamiltonian(state, .3, .7, PARAMETERS.c)
        assert hamiltonian(state, PARAMETERS) == pytest.approx(original, rel=3e-15, abs=3e-16)
        g = gradient(state, .3, .7, PARAMETERS.c)
        expected = np.r_[g[3:6], -g[:3], np.cross(g[6:], state[6:])]
        assert np.linalg.norm(rhs(0, state, PARAMETERS)-expected) < 1e-12


def test_total_moment_derivative_and_energy_derivative_with_SO_reaction():
    derivative = rhs(0, STATE, PARAMETERS)
    dj = np.cross(derivative[:3], STATE[3:6])+np.cross(STATE[:3], derivative[3:6])+derivative[6:]
    assert np.linalg.norm(derivative[6:]) > 1e-8
    assert np.linalg.norm(dj) < 1e-16
    assert abs(np.dot(gradient(STATE, .3, .7, PARAMETERS.c), derivative)) < 1e-15
    assert abs(np.dot(STATE[6:], derivative[6:])) < 1e-21
    # Removing orbital SO response leaves a resolved, nonzero total-J derivative.
    wrong = rhs(0, STATE, PARAMETERS, spin_orbit=False)
    wrong[6:] = derivative[6:]
    bad_dj = np.cross(wrong[:3], STATE[3:6])+np.cross(STATE[:3], wrong[3:6])+wrong[6:]
    assert np.linalg.norm(bad_dj) > 1e-8


def test_SO_flow_matches_derived_exact_rotations_and_radial_shear():
    times = np.linspace(0., 200., 33)
    solution = solve_ivp(lambda t, y: rhs(t, y, PARAMETERS, only_so=True),
                         (0., times[-1]), STATE, t_eval=times, rtol=1e-12, atol=1e-14)
    assert solution.success
    expected = np.array([exact_so(STATE, t, PARAMETERS) for t in times])
    assert np.max(np.linalg.norm(solution.y.T-expected, axis=1)) < 1e-12
    # Both opposite orbital/spin exchanges are present, not only a precession angle.
    old_l = np.cross(STATE[:3], STATE[3:6]); new_l = np.cross(expected[-1, :3], expected[-1, 3:6])
    assert np.linalg.norm(new_l-old_l) > 1e-6
    assert np.linalg.norm(new_l-old_l+expected[-1, 6:]-STATE[6:]) < 1e-16


def test_rotation_covariance_time_reversal_and_newton_limit():
    matrix = Rotation.from_rotvec([.3, -.4, .2]).as_matrix()
    rotated = (STATE.reshape(3, 3)@matrix.T).ravel()
    assert np.linalg.norm(rhs(0, rotated, PARAMETERS)-
                          (rhs(0, STATE, PARAMETERS).reshape(3, 3)@matrix.T).ravel()) < 3e-16
    signs = np.r_[np.ones(3), -np.ones(6)]
    assert np.linalg.norm(rhs(0, STATE*signs, PARAMETERS)+rhs(0, STATE, PARAMETERS)*signs) < 1e-16
    result = rhs(0, STATE, Parameters(.3, .7, 1e100))
    expected = np.r_[STATE[3:6]/.21, -.21*STATE[:3]/np.linalg.norm(STATE[:3])**3, np.zeros(3)]
    assert np.linalg.norm(result-expected) < 3e-16
    assert np.linalg.norm(rhs(0, STATE, PARAMETERS)[:3]-STATE[3:6]/.21) > 1e-6


def test_test_mass_geodetic_coefficient_limit():
    # omega_SO=(G/c²r³)(2+3m2/(2m1))*mu*(r×v) -> (3Gm2/2c²r³)(r×v).
    p = Parameters(1e-10, 1., 1000.)
    assert p.spin_coefficient*p.reduced == pytest.approx(1.5/p.c**2, rel=1e-9)


def test_spinless_canonical_acceleration_matches_EIH_to_retained_order():
    state = STATE.copy(); state[6:] = 0.
    discrepancies = []
    for c in [float(np.sqrt(5e4)), float(np.sqrt(1e5))]:
        parameters = Parameters(.3, .7, c)
        flow = rhs(0, state, parameters)
        h = 1e-3
        velocity_at = lambda offset: rhs(0, state+offset*flow, parameters)[:3]
        acceleration = (velocity_at(-2*h)-8*velocity_at(-h)+8*velocity_at(h)-velocity_at(2*h))/(12*h)
        positions = np.array([.7*state[:3], -.3*state[:3]])
        velocities = np.array([.7*flow[:3], -.3*flow[:3]])
        point = eih_acceleration(positions, velocities, np.array([.3, .7])/G, c=c)
        discrepancies.append(np.linalg.norm(acceleration-(point[0]-point[1])))
    assert 3.8 < discrepancies[0]/discrepancies[1] < 4.2
    assert discrepancies[0] < 1e-7


@pytest.mark.parametrize('state', [np.zeros(9), np.r_[STATE[:8], np.nan],
                                  np.r_[STATE[:6], [100., 0., 0.]], STATE*1e4])
def test_reject_unsupported_research_domain(state):
    with pytest.raises(ValueError):
        rhs(0, state, PARAMETERS)
