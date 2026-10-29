"""Ready application profiles using the already validated physical models."""
from dataclasses import replace

from .experiment import create_experiment, preset


def two_q2_demo(*, backend="python"):
    """Exact synthetic two-body IC from380; no real planetary parameters."""
    import hashlib
    import json
    from importlib.resources import files
    from .storage import from_document
    raw=files('solar_simulator.data').joinpath('two-q2-demo380.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!='3f6fa9b5883db9e14653c43ddc7359e4cf795744e42d3345baf9ea018772428b':
        raise ValueError('Учебные начальные данные двух Q2-фигур изменены')
    result=from_document(json.loads(raw))
    return replace(result,settings=replace(result.settings,backend=backend))


def scenario(name, *, backend="python", eccentricity=0.0):
    """Prepare new controls explicitly; contacts retain their Verlet model."""
    result = preset(name, backend=backend, eccentricity=eccentricity)
    if not any(body.radius > 0 for body in result.bodies):
        result = replace(result, settings=replace(result.settings, integrator="dop853"))
    return result


def lunar_rotation(*, backend="python"):
    """The Newtonian rigid-Moon profile previously shipped in portable builds."""
    from .nbody_rotation import lunar_initial
    result = preset("solar-system-moon", backend=backend)
    settings = replace(result.settings, integrator="dop853", physics="newtonian",
                       relative_pair=("Earth", "Moon"), error_control="per-body",
                       rtol=1e-13, position_atol=1e-7, velocity_atol=1e-13)
    return create_experiment(result.bodies, settings, origin=result.origin,
                             rotations=lunar_initial(result.bodies, result.origin))


def solar_sandbox(*, backend="python"):
    """Ten-body EIH plus fixed Sun/Earth J2, qualified at 45/13 epochs for a year.

    The axes are prescribed constants, not dynamically integrated rotations.
    Qualification applies to the unchanged pinned start, not edited systems.
    """
    from .oblateness import solar_j2, earth_j2
    result = preset("solar-system-moon", backend=backend)
    settings = replace(result.settings, integrator="dop853", physics="eih-1pn",
        figures=solar_j2(result.bodies, result.origin)+earth_j2(result.bodies, result.origin),
        relative_pair=("Earth", "Moon"), error_control="per-body", rtol=1e-13,
        position_atol=1e-3, velocity_atol=1e-9)
    return create_experiment(result.bodies, settings, origin=result.origin)
