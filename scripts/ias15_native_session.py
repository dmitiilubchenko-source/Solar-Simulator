"""Explicit native-Newton research variant sharing the owned session lifecycle."""
from scripts.ias15_native_newton import NewtonCallback, guard
from scripts.ias15_restart import simulation
from scripts.ias15_session import IAS15Session
from scripts.native_audit import require_native
from solar_simulator.native_forces import prepare


class IAS15NativeSession(IAS15Session):
    def _create_simulation(self, library, masses, initial, counter):
        require_native()
        native = prepare(masses)
        self._callback = NewtonCallback(lambda p, v: native(p, v, None, None))
        self._count_forces = True
        sim = simulation(library, 0., masses, initial, self._packet_dt, self._epsilon)
        sim.gravity, sim.force_is_velocity_dependent = 'none', 0
        sim.additional_forces = self._callback
        guard(sim, masses, self._epsilon, 'native')
        return sim

    def _integrate(self, end):
        self._verify_simulation()
        try:
            self._sim.integrate(end, exact_finish_time=1)
        finally:
            self._force_calls[0] = self._callback.calls
            try:
                self._callback.check()
            except RuntimeError as error:
                raise RuntimeError('Native IAS15 callback failed; previous snapshot preserved') from error.__cause__

    def _verify_simulation(self):
        guard(self._sim, self._masses, self._epsilon, 'native')

    def next(self, *, until=None):
        try:
            return super().next(until=until)
        finally:
            # JSON/model checks can fail after _integrate has already returned.
            if self._failed:
                self._callback = None

    def close(self):
        super().close()
        self._callback = None
