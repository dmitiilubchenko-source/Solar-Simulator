from math import pi, sqrt
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.ias15_reference import load_library
from scripts.ias15_restart import bits, restore
from scripts.ias15_session import IAS15Session
from solar_simulator.simulation import G


class FakeSimulation:
    """Fault injection after a real mutation of a private controller, not a force oracle."""
    def __init__(self, fault):
        self.fault = fault
        self.particles, self.calls = [], []
        self.steps_done, self.additional_forces = 0, None

    @property
    def integrator(self):
        return self._integrator

    @integrator.setter
    def integrator(self, name):
        assert name == 'ias15'
        self._integrator = SimpleNamespace()

    @property
    def N(self):
        return len(self.particles)

    def add(self, **kwargs):
        self.particles.append(SimpleNamespace(**kwargs))

    def integrate(self, end, *, exact_finish_time):
        assert exact_finish_time == 1
        self.calls.append(end)
        for p in self.particles:
            p.x += (end-self.t)*p.vx
        self.t, self.steps_done = end, self.steps_done+1
        if self.additional_forces is not None:
            self.additional_forces(None)
        if len(self.calls) != 2:
            return
        if self.fault == 'exception':
            raise OSError('injected after controller mutation')
        if self.fault == 'interrupt':
            raise KeyboardInterrupt('injected inside packet')
        if self.fault == 'time':
            self.t = float(np.nextafter(end, -np.inf))
        if self.fault == 'nan':
            self.particles[0].x = np.nan
        if self.fault == 'mass':
            self.particles[0].m *= 2
        if self.fault == 'model':
            self.G *= 2
        if self.fault == 'counter':
            self.steps_done = 0


class FakeLibrary:
    __version__ = '5.2.2'

    def __init__(self, fault=None):
        self.fault, self.instances = fault, []

    def Simulation(self):
        result = FakeSimulation(self.fault)
        self.instances.append(result)
        return result


def make_session(library, target=25., count=False):
    return IAS15Session([1., 2.], [[-1., 0., 0., .2, 0., 0.], [1., 0., 0., -.1, 0., 0.]],
                        10., target, library, 1e-9, 'input', count_forces=count)


def identity(value):
    return (bits(value.time), bits(value.masses), bits(value.state), value.origin,
            value.checkpoint_json, value.checkpoint_sha256)


@pytest.mark.parametrize('fault', ['exception', 'interrupt', 'time', 'nan', 'mass', 'model', 'counter', 'json'])
def test_partial_failure_never_publishes_mutated_state_or_allows_resume(fault, monkeypatch):
    library = FakeLibrary(fault)
    session = make_session(library, count=True)
    previous = session.next()
    stats = session.statistics
    if fault == 'json':
        import scripts.ias15_session as module
        def broken(*args):
            raise OSError('injected JSON validation failure')
        monkeypatch.setattr(module, 'checkpoint', broken)
    with pytest.raises(BaseException):
        session.next()
    assert identity(session.current) == identity(previous)
    after = session.statistics
    assert after['failed'] and after['packets'] == stats['packets'] == 1
    assert after['steps_done'] == stats['steps_done'] == 1
    assert after['force_evaluations'] == stats['force_evaluations'] == 1
    assert after['attempted_force_evaluations'] == 2 and after['attempts'] == 2
    assert library.instances[0].particles[0].x != previous.state[0, 0]
    with pytest.raises(RuntimeError, match='failed'):
        session.next(until=previous.time)
    assert len(library.instances) == 1 and len(library.instances[0].calls) == 2
    session.close()
    assert identity(session.current) == identity(previous)


def test_inputs_outputs_and_statistics_are_independent_and_controller_is_owned():
    library = FakeLibrary()
    masses = np.array([1., 2.])
    initial = np.array([[-1., -0., 0., .2, 0., 0.], [1., 0., 0., -.1, 0., 0.]])
    session = IAS15Session(masses, initial, 10., 25., library, 1e-9, 'input')
    original = identity(session.current)
    masses[:] = 99
    initial[:] = 99
    a, b = session.current, session.current
    a.masses[:] = 88
    a.state[:] = 88
    assert identity(session.current) == original == identity(b)
    first = session.next()
    expected = identity(session.current)
    first.state[:] = -5
    first.masses[:] = -5
    session.statistics.update(packets=100, failed=True)
    assert identity(session.current) == expected and session.statistics['packets'] == 1
    _, m, q = restore(session.current.checkpoint_json, session.current.checkpoint_sha256, 'input')
    assert bits(m) == bits([1., 2.]) and bits(q) == bits(session.current.state)
    session.next()
    final = session.next()
    assert final.time == 25. and session.finished
    assert library.instances[0].calls == [10., 20., 25.]
    assert len(library.instances) == 1


@pytest.mark.parametrize('limit', [-1., 26., float('nan'), float('inf'), True, '10'])
def test_invalid_limits_do_not_call_or_poison_controller(limit):
    library = FakeLibrary()
    session = make_session(library)
    before = identity(session.current)
    with pytest.raises(ValueError):
        session.next(until=limit)
    assert identity(session.current) == before and not session.statistics['failed']
    assert library.instances[0].calls == []
    assert session.next().time == 10.


def test_noops_close_context_manager_and_fractional_endpoint():
    library = FakeLibrary()
    session = make_session(library, 3.125)
    assert session.next(until=0.).time == 0. and session.statistics['attempts'] == 0
    with session:
        final = session.next()
        assert final.time == 3.125
        assert identity(session.next()) == identity(final)
        assert library.instances[0].calls == [3.125]
    assert session.statistics['closed'] and session.finished
    session.close()
    assert identity(session.current) == identity(final)
    with pytest.raises(RuntimeError, match='closed'):
        session.next()
    other = make_session(FakeLibrary())
    with pytest.raises(OSError):
        with other:
            raise OSError('caller failure')
    assert other.statistics['closed'] and other.current.time == 0.


def test_unrepresentable_late_packet_is_rejected_before_integrating():
    from dataclasses import replace
    library = FakeLibrary()
    session = make_session(library, 1e20+1e6)
    # Seed an abstract late committed state to test the time guard without 1e19 calls.
    session._committed = (replace(session.current, time=1e20), 1, 1, 0)
    session._sim.t = 1e20
    before = identity(session.current)
    with pytest.raises(ValueError, match='advance'):
        session.next()
    assert identity(session.current) == before and not session.statistics['failed']
    assert library.instances[0].calls == []


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_previous_session_audits_cannot_be_overwritten(tmp_path, suffix):
    from scripts.assess_ias15_session import run
    output = tmp_path/'result.json'
    output.with_suffix(suffix).write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        run(output, tmp_path, tmp_path)
    assert output.with_suffix(suffix).read_bytes() == b'keep'


@pytest.fixture
def library():
    path = Path(__file__).resolve().parents[1]/'.tools/ias15165/dependency'
    if path.is_dir():
        return load_library(path)
    pytest.importorskip('rebound', reason='Optional isolated IAS15 research package is absent')
    return load_library()


@pytest.mark.parametrize('epsilon', [1e-9, 1e-11])
def test_real_owned_session_matches_independent_inclined_circle(library, epsilon):
    mass, radius = 1e20, 1e7
    omega = sqrt(2*G*mass/radius**3)
    period = 2*pi/omega
    initial = [[-radius/2, 0., 0., 0., -.3*radius*omega, -.4*radius*omega],
               [radius/2, 0., 0., 0., .3*radius*omega, .4*radius*omega]]
    times = [0., period/4, period/2, period, 2*period]
    with IAS15Session([mass, mass], initial, period/50, times[-1], library, epsilon, 'circle') as session:
        previous = session.current
        for time in times:
            while session.current.time < time:
                session.next(until=float(time))
            row = session.current
            c, s = np.cos(omega*time), np.sin(omega*time)
            expected_p = radius*np.array([c, .6*s, .8*s])
            expected_v = radius*omega*np.array([-s, .6*c, .8*c])
            relative = row.state[1]-row.state[0]
            assert np.linalg.norm(relative[:3]-expected_p) < 1e-3
            assert np.linalg.norm(relative[3:]-expected_v) < 1e-8
        assert previous.time == 0 and bits(previous.state) == bits(initial)
