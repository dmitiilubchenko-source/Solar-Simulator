"""Independent Hamiltonian-gradient and exact flat-Lorentz boundary oracles.

No sr_cloud or local_event_map imports. SI; positive rest masses, -+++.
This code operates on the already validated synthetic audit inputs.
"""
import numpy as np


def scalar_hamiltonian(momentum, masses, c):
    return np.sum(np.sqrt(np.asarray(masses)**2*c**4+c**2*np.sum(momentum*momentum, axis=-1)), axis=-1)


def gradient_velocity(momentum, masses, c):
    flat = np.asarray(momentum).ravel(); size = len(flat); step = 1e-20
    probes = (flat[None, :]+1j*step*np.eye(size)).reshape(size, len(masses), 3)
    return (scalar_hamiltonian(probes, masses, c).imag/step).reshape(len(masses), 3)


def rhs(unit_time, state, masses, c, duration, length_scale, momentum_scale):
    count = len(masses); z = state.reshape(2, count, 3)
    velocity = gradient_velocity(z[1]*momentum_scale, masses, c)
    return np.r_[duration*velocity.ravel()/length_scale, np.zeros(count*3)]


def flat_local_event(global_time, global_position, frame_velocity, c):
    """Direct inverse Lorentz boost, no PN polynomial or production matrix."""
    v = np.asarray(frame_velocity); x = np.asarray(global_position)
    beta2 = (v@v)/c**2; gamma = 1/np.sqrt(1-beta2)
    coefficient = gamma**2/(gamma+1)/c**2
    local_time = gamma*(global_time-v@x/c**2)
    local_position = x+coefficient*v*(v@x)-gamma*v*global_time
    return local_time, local_position


def flat_local_velocity(global_velocity, frame_velocity, c):
    v = np.asarray(frame_velocity); u = np.asarray(global_velocity)
    gamma = 1/np.sqrt(1-v@v/c**2)
    spatial = u+gamma**2/(gamma+1)/c**2*v*(v@u)-gamma*v
    rate = gamma*(1-v@u/c**2)
    return spatial/rate
