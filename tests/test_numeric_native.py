"""The Python facade must validate before dispatching to the native solver."""
import numpy as np
import pytest

from solar_simulator import rust_backend
from solar_simulator.experiment import Settings, create_experiment, advance
from solar_simulator.simulation import Body
from solar_simulator.storage import from_document, to_document
from solar_simulator.sandbox import branch_experiment
from solar_simulator.vector3 import Vector3 as V


@pytest.mark.parametrize("integrator", ("verlet", "dop853"))
@pytest.mark.parametrize("backend", ("python", "rust"))
def test_numpy_objects_remain_persistable_after_both_integrators_and_backends(backend, integrator):
    if backend == "rust":
        pytest.importorskip("solar_native")
    e = create_experiment([Body("A", np.float64(1), V(np.float32(0), 0, 0),
                               V(np.float64(1), 0, 0), np.int64(0))],
                          Settings(np.float64(1), backend=backend, integrator=integrator))
    doc = to_document(advance(e, 2))
    loaded = from_document(doc)
    assert to_document(loaded) == doc
    assert branch_experiment(loaded).child.bodies[0].position.x == 2


@pytest.mark.parametrize("value", (True, False, np.bool_(True), np.bool_(False), float("nan"), float("inf")))
def test_native_facades_reject_invalid_scalars_before_loading_or_dispatch(value, monkeypatch):
    import sys
    class Forbidden:
        def __getattr__(self, name):
            raise AssertionError("Invalid input reached native dispatch")
    monkeypatch.setitem(sys.modules, "solar_native", Forbidden())
    for call in (lambda: rust_backend.evolve([], value, 0),
                 lambda: rust_backend.run_until_contact([], value, 0),
                 lambda: rust_backend.resolve_contact([], 0, 1, value),
                 lambda: rust_backend.simulate_collisions([], value, 0, 1., 1),
                 lambda: rust_backend.simulate_collisions([], 1., 0, value, 1)):
        with pytest.raises(ValueError):
            call()
