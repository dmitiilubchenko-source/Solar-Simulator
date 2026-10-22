from types import SimpleNamespace

import numpy as np
import pytest

import scripts.ias15_native_session as native_module
from scripts.ias15_native_session import IAS15NativeSession
from scripts.ias15_restart import bits
from test_ias15_native_newton import circle, library
from test_ias15_session import FakeLibrary, FakeSimulation, identity


class NativeFakeSimulation(FakeSimulation):
    """Mutate private state before failure; a contract probe, not a physical integrator."""
    def stop(self):
        pass

    def integrate(self, end, *, exact_finish_time):
        assert exact_finish_time == 1
        self.calls.append(end)
        for particle in self.particles:
            particle.x += (end-self.t)*particle.vx
        self.t, self.steps_done = end, self.steps_done+1
        self.additional_forces(SimpleNamespace(contents=self))
        if len(self.calls) != 2:
            return
        if self.fault == 'exception':
            raise OSError('after private mutation')
        if self.fault == 'interrupt':
            raise KeyboardInterrupt('after private mutation')
        if self.fault == 'time':
            self.t = float(np.nextafter(end, -np.inf))
        if self.fault == 'nan':
            self.particles[0].x = np.nan
        if self.fault == 'mass':
            self.particles[0].m *= 2
        if self.fault == 'model':
            self.G *= 2
        if self.fault == 'gravity':
            self.gravity = 'basic'
        if self.fault == 'velocity':
            self.force_is_velocity_dependent = 1
        if self.fault == 'counter':
            self.steps_done = 0


class NativeFakeLibrary(FakeLibrary):
    def Simulation(self):
        result = NativeFakeSimulation(self.fault)
        self.instances.append(result)
        return result


def make(library, target=25.):
    return IAS15NativeSession([1., 2.], [[-1., 0., 0., .2, 0., 0.], [1., 0., 0., -.1, 0., 0.]],
                              10., target, library, 1e-9, 'native-input')


@pytest.mark.parametrize('fault', ['exception', 'interrupt', 'time', 'nan', 'mass', 'model',
                                  'gravity', 'velocity', 'counter', 'json'])
def test_native_failure_after_mutation_preserves_joint_commit_and_releases_controller(fault, monkeypatch):
    library = NativeFakeLibrary(fault)
    session = make(library)
    previous = session.next()
    old = session.statistics
    if fault == 'json':
        import scripts.ias15_session as common
        def broken(*args):
            raise OSError('physical JSON failed after successful integrate')
        monkeypatch.setattr(common, 'checkpoint', broken)
    with pytest.raises(BaseException):
        session.next()
    stats = session.statistics
    assert identity(session.current) == identity(previous)
    assert stats['failed'] and stats['attempts'] == 2 and stats['attempted_force_evaluations'] == 2
    assert all(stats[k] == old[k] == 1 for k in ('packets', 'steps_done', 'force_evaluations'))
    assert session._sim is None and session._callback is None
    assert len(library.instances) == 1 and library.instances[0].particles[0].x != previous.state[0, 0]
    with pytest.raises(RuntimeError, match='failed'):
        session.next(until=previous.time)
    session.close()
    assert identity(session.current) == identity(previous)


@pytest.mark.parametrize('failure', ['exception', 'nan', 'shape', 'interrupt'])
def test_real_native_callback_error_after_one_successful_packet_preserves_old_snapshot(library, failure, capsys):
    request, _ = circle()
    with IAS15NativeSession(request['masses'], request['states'], request['packet_dt'], request['times'][-1],
                            library, 1e-9, 'circle') as session:
        previous = session.next()
        old = session.statistics
        def bad(p, v):
            if failure == 'exception':
                raise ValueError('injected native failure')
            if failure == 'interrupt':
                raise KeyboardInterrupt('injected interruption')
            return np.full_like(p, np.nan) if failure == 'nan' else np.zeros(3)
        session._callback.force = bad
        with pytest.raises(RuntimeError) as error:
            session.next()
        assert isinstance(error.value.__cause__, KeyboardInterrupt if failure == 'interrupt' else ValueError)
        assert identity(session.current) == identity(previous)
        stats = session.statistics
        assert stats['failed'] and stats['attempted_force_evaluations'] > stats['force_evaluations']
        assert all(stats[k] == old[k] for k in ('packets', 'steps_done', 'force_evaluations'))
        assert session._sim is None and session._callback is None
        with pytest.raises(RuntimeError, match='failed'):
            session.next()
    assert 'Exception ignored' not in capsys.readouterr().err


def test_native_inputs_outputs_statistics_noops_fractional_finish_and_close_are_owned():
    library = NativeFakeLibrary()
    masses = np.array([1., 2.])
    states = np.array([[-1., -0., 0., .2, 0., 0.], [1., 0., 0., -.1, 0., 0.]])
    session = IAS15NativeSession(masses, states, 10., 13.125, library, 1e-9, 'alias')
    original = identity(session.current)
    masses[:] = states[:] = 88.
    first, second = session.current, session.current
    first.state[:] = first.masses[:] = 99.
    assert identity(second) == identity(session.current) == original
    assert session.next(until=0.).time == 0. and library.instances[0].calls == []
    result = session.next()
    result.state[:] = 50.
    assert session.current.state[0, 0] != 50.
    session.statistics.update(packets=99, failed=True)
    assert session.statistics['packets'] == 1 and not session.statistics['failed']
    with session:
        final = session.next()
        assert final.time == 13.125 and session.finished
        assert identity(session.next()) == identity(final)
    session.close()
    assert session._sim is None and session._callback is None and identity(session.current) == identity(final)
    assert len(library.instances) == 1 and library.instances[0].calls == [10., 13.125]
    with pytest.raises(RuntimeError, match='closed'):
        session.next()


@pytest.mark.parametrize('until', [-1., 30., float('nan'), float('inf'), True, '10'])
def test_bad_limits_do_not_call_or_poison_native_session(until):
    library = NativeFakeLibrary()
    with make(library) as session:
        before = identity(session.current)
        with pytest.raises(ValueError):
            session.next(until=until)
        assert identity(session.current) == before and not session.statistics['failed']
        assert library.instances[0].calls == [] and session.next().time == 10.


def test_double_gravity_before_packet_never_calls_integrator_or_commits():
    library = NativeFakeLibrary()
    session = make(library)
    previous = session.next()
    session._sim.gravity = 'basic'
    with pytest.raises(ArithmeticError, match='double gravity'):
        session.next()
    assert identity(session.current) == identity(previous) and library.instances[0].calls == [10.]
    assert session.statistics['failed'] and session._sim is None and session._callback is None


@pytest.mark.parametrize('epsilon', [1e-9, 1e-11])
def test_real_native_session_against_independent_inclined_circle(library, epsilon):
    request, expected = circle()
    actual = []
    with IAS15NativeSession(request['masses'], request['states'], request['packet_dt'], request['times'][-1],
                            library, epsilon, 'analytic-circle') as session:
        for epoch in request['times']:
            while session.current.time < epoch:
                session.next(until=float(epoch))
            actual.append(session.current.state)
    actual = np.asarray(actual)
    assert np.max(np.linalg.norm(actual[:, :, :3]-expected[:, :, :3], axis=2)) < .1
    assert np.max(np.linalg.norm(actual[:, :, 3:]-expected[:, :, 3:], axis=2)) < 1e-6
    assert bits(actual[0]) == bits(request['states']) and session.statistics['simulations'] == 1


def test_missing_native_fails_before_creating_any_controller(monkeypatch):
    def missing():
        raise RuntimeError('real native unavailable')
    monkeypatch.setattr(native_module, 'require_native', missing)
    library = NativeFakeLibrary()
    with pytest.raises(RuntimeError, match='native unavailable'):
        make(library)
    assert not library.instances


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_previous_native_session_audits_cannot_be_overwritten(tmp_path, suffix):
    from scripts.assess_ias15_native_session import run
    output = tmp_path/'result.json'
    output.with_suffix(suffix).write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        run(output, tmp_path, tmp_path)
    assert output.with_suffix(suffix).read_bytes() == b'keep'


def test_unsupported_mode_is_rejected_before_controller_creation():
    from scripts.assess_ias15_native_session import trajectory
    with pytest.raises(ValueError, match='Undeclared'):
        trajectory({}, None, 1e-9, 'bad', 'unsupported')
