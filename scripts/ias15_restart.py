"""Research-only physical checkpoints; never registers an application backend."""
import hashlib
import json

import numpy as np

from scripts.ias15_reference import EPSILONS, VERSION, packet_end
from solar_simulator.simulation import G

MODES = ('warm', 'one-cold', 'every-packet')


def bits(values):
    return np.asarray(values, dtype='>f8').tobytes()


def physical(time, masses, state):
    masses, state = np.asarray(masses, dtype=float), np.asarray(state, dtype=float)
    if (type(time) not in (int, float) or not np.isfinite(time) or time < 0
            or masses.shape != (2,) or state.shape != (2, 6)
            or not np.isfinite(masses).all() or not (masses > 0).all()
            or not np.isfinite(state).all()):
        raise ValueError('Expected finite two-body physical state and nonnegative time')
    return float(time), masses.copy(), state.copy()


def checkpoint(time, masses, state, origin):
    time, masses, state = physical(time, masses, state)
    if not isinstance(origin, str) or not origin:
        raise ValueError('Checkpoint requires its input provenance')
    document = dict(schema='ias15-research-physical-v1', solver='IAS15 research',
                    model='Newtonian point masses', units='SI', G=G, origin=origin,
                    time=time, masses=masses.tolist(), states=state.tolist())
    raw = json.dumps(document, sort_keys=True, separators=(',', ':'), allow_nan=False)
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    restored = restore(raw, digest, origin)
    if any(bits(a) != bits(b) for a, b in zip((time, masses, state), restored)):
        raise ArithmeticError('Physical checkpoint roundtrip changed binary64 values')
    return raw, digest


def restore(raw, digest, origin):
    if hashlib.sha256(raw.encode('utf-8')).hexdigest() != digest:
        raise ValueError('Physical checkpoint SHA mismatch')
    value = json.loads(raw)
    if (set(value) != {'schema', 'solver', 'model', 'units', 'G', 'origin', 'time', 'masses', 'states'}
            or value['schema'] != 'ias15-research-physical-v1' or value['solver'] != 'IAS15 research'
            or value['model'] != 'Newtonian point masses' or value['units'] != 'SI'
            or type(value['G']) is not float or value['G'] != G or value['origin'] != origin):
        raise ValueError('Wrong checkpoint model, units, G or origin')
    if (any(type(x) not in (int, float) for x in value['masses'])
            or any(type(x) not in (int, float) for row in value['states'] for x in row)):
        raise ValueError('Expected numeric checkpoint components')
    return physical(value['time'], value['masses'], value['states'])


def validate(masses, initial, times, packet_dt, epsilon, mode):
    _, masses, initial = physical(0., masses, initial)
    times = np.asarray(times, dtype=float)
    if (times.ndim != 1 or len(times) < 2 or not np.isfinite(times).all()
            or times[0] != 0 or not (np.diff(times) > 0).all()):
        raise ValueError('Expected strictly increasing finite epoch grid from zero')
    if (type(packet_dt) not in (int, float) or not np.isfinite(packet_dt) or packet_dt <= 0
            or packet_dt/200 == 0 or epsilon not in EPSILONS or mode not in MODES):
        raise ValueError('Undeclared mode, epsilon or invalid packet interval')
    middle = int(np.searchsorted(times, times[-1]/2))
    if mode == 'one-cold' and middle == len(times)-1:
        raise ValueError('One-cold mode requires a middle output epoch')
    return masses, initial, times, middle


def simulation(library, time, masses, state, packet_dt, epsilon, counter=None):
    if library.__version__ != VERSION:
        raise ValueError('Expected pinned REBOUND '+VERSION)
    sim = library.Simulation()
    sim.G, sim.gravity, sim.softening = G, 'basic', 0.
    sim.integrator = 'ias15'
    sim.integrator.epsilon, sim.integrator.adaptive_mode = epsilon, 'PRS23'
    sim.integrator.min_dt, sim.dt, sim.t = 0., packet_dt/200, time
    for mass, row in zip(masses, state):
        sim.add(m=float(mass), x=row[0], y=row[1], z=row[2], vx=row[3], vy=row[4], vz=row[5])
    if counter is not None:
        sim.additional_forces = counter
    if (sim.G != G or sim.gravity != 'basic' or sim.softening != 0 or sim.N != 2
            or sim.integrator.epsilon != epsilon or sim.integrator.adaptive_mode != 'PRS23'
            or sim.integrator.min_dt != 0 or sim.dt != packet_dt/200 or sim.t != time
            or bits([p.m for p in sim.particles]) != bits(masses) or bits(snapshot(sim)) != bits(state)):
        raise ArithmeticError('IAS15 initial physical state or settings changed')
    return sim


def snapshot(sim):
    return np.asarray([[p.x, p.y, p.z, p.vx, p.vy, p.vz] for p in sim.particles])


def trajectory(masses, initial, times, packet_dt, library, epsilon, mode, origin, *, count_forces=False):
    masses, initial, times, middle = validate(masses, initial, times, packet_dt, epsilon, mode)
    calls = 0
    def counter(pointer):
        nonlocal calls
        calls += 1
    raw, digest = checkpoint(0., masses, initial, origin)
    sim = simulation(library, *restore(raw, digest, origin), packet_dt, epsilon,
                     counter if count_forces else None)
    documents, digests, packet_states, endpoints = [raw], [digest], [initial.copy()], [0.]
    restarts, values, completed_steps = [], [], 0
    pending = False
    for epoch in times:
        while sim.t < epoch:
            if pending:
                completed_steps += int(sim.steps_done)
                sim = simulation(library, *restore(documents[-1], digests[-1], origin), packet_dt,
                                 epsilon, counter if count_forces else None)
                restarts.append(len(endpoints)-1)
                pending = False
            end = packet_end(float(sim.t), float(epoch), packet_dt)
            sim.integrate(end, exact_finish_time=1)
            if sim.t != end:
                raise RuntimeError('IAS15 did not reach the exact packet endpoint')
            state = snapshot(sim)
            raw, digest = checkpoint(float(sim.t), masses, state, origin)
            documents.append(raw)
            digests.append(digest)
            packet_states.append(state)
            endpoints.append(end)
            pending = mode == 'every-packet' or (mode == 'one-cold' and end == times[middle])
        values.append(snapshot(sim))
    statistics = dict(mode=mode, epsilon=epsilon, packets=len(endpoints)-1,
        simulations=1+len(restarts), restart_packet_indices=restarts,
        restart_output_index=middle if mode == 'one-cold' else None,
        steps_done=completed_steps+int(sim.steps_done),
        force_evaluations=calls if count_forces else None, initial_dt_seconds=packet_dt/200,
        physical_roundtrip_bitexact=True, adaptive_mode='PRS23', gravity='basic')
    artifacts = dict(packet_endpoints=np.asarray(endpoints), packet_states=np.asarray(packet_states),
                     checkpoint_json=np.asarray(documents), checkpoint_sha256=np.asarray(digests))
    return np.asarray(values), statistics, artifacts
