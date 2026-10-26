"""Physical numeric inputs must remain usable by the strict checkpoint codec."""
from decimal import Decimal

import numpy as np
import pytest

from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.nbody_rotation import RotationState
from solar_simulator.rotation import RigidFigure, pair_field, rotation_matrix
from solar_simulator.sandbox import branch_experiment
from solar_simulator.simulation import Body, step, sun_earth
from solar_simulator.storage import from_document, to_document
from solar_simulator.vector3 import Vector3 as V

TYPES = (int, float, np.int8, np.int16, np.int32, np.int64,
         np.uint8, np.uint16, np.uint32, np.uint64,
         np.float16, np.float32, np.float64)
BAD = (True, False, np.bool_(True), np.bool_(False),
       float("nan"), float("inf"), -float("inf"),
       np.float64("nan"), np.float32("inf"),
       1j, np.complex128(1), "1", Decimal("1"), np.array(1.0), 10**400,
       np.timedelta64(1, 'Y'), np.timedelta64(1, 's'), np.datetime64('2026-01-01'))


def body(**changes):
    values = dict(name="A", mass=1., position=V(0, 0, 0),
                  velocity=V(1, 0, 0), radius=0., spin=V(0, 0, 0))
    values.update(changes)
    return Body(**values)


@pytest.mark.parametrize("value", BAD)
@pytest.mark.parametrize("axis", range(3))
def test_vector_rejects_invalid_scalar_before_arithmetic(value, axis):
    values = [0., 0., 0.]
    values[axis] = value
    with pytest.raises(ValueError):
        V(*values)


@pytest.mark.parametrize("value", BAD)
@pytest.mark.parametrize("field", ("mass", "radius"))
def test_body_rejects_invalid_scalar(value, field):
    with pytest.raises(ValueError):
        body(**{field: value})


@pytest.mark.parametrize("value", BAD)
@pytest.mark.parametrize("field", ("mass", "bounding_radius", "moments"))
def test_figure_checks_types_before_float_coercion(value, field):
    values = dict(mass=1., moments=(2., 2., 2.), bounding_radius=4.)
    values[field] = (value, 2., 2.) if field == "moments" else value
    with pytest.raises(ValueError):
        RigidFigure(**values)


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize("value", (True, False, np.bool_(True), np.bool_(False)))
def test_each_principal_moment_rejects_bool(index, value):
    moments = [2., 2., 2.]; moments[index] = value
    with pytest.raises(ValueError):
        RigidFigure(1., moments, 4.)


@pytest.mark.parametrize("field,index", [("quaternion", i) for i in range(4)] + [("angular_momentum", i) for i in range(3)])
@pytest.mark.parametrize("value", (True, False, np.bool_(True), np.bool_(False)))
def test_each_rotation_component_rejects_bool(field, index, value):
    fields = dict(quaternion=[1., 0., 0., 0.], angular_momentum=[0., 0., 1.])
    fields[field][index] = value
    with pytest.raises(ValueError):
        RotationState("A", RigidFigure(1., (2.,)*3, 4.), quaternion_atol=1e-12,
                      momentum_atol=1e-12, **fields)


@pytest.mark.parametrize("type_", TYPES)
def test_supported_scalars_create_advance_serialize_load_and_branch(type_):
    b = body(mass=type_(1), position=V(type_(0), type_(0), type_(0)),
             velocity=V(type_(1), type_(0), type_(0)), radius=type_(0),
             spin=V(type_(0), type_(0), type_(0)))
    e = advance(create_experiment([b], Settings(type_(1))), 2)
    document = to_document(e)
    restored = from_document(document)
    assert to_document(restored) == document
    branch = branch_experiment(restored)
    assert branch.parent.bodies[0].position.x == 2
    assert branch.child.time == 0
    assert to_document(advance(branch.child, 1))["bodies"][0]["position"][0] == 3
    assert type(b.mass) in (int, float)
    assert type(b.radius) in (int, float)
    assert all(type(v) in (int, float) for v in vars(b.position).values())


@pytest.mark.parametrize("type_", TYPES)
def test_rotation_scalars_roundtrip_schema10_without_changing_branch_guards(type_):
    f = RigidFigure(type_(1), (type_(2),)*3, type_(4))
    r = RotationState("A", f, (type_(1), type_(0), type_(0), type_(0)),
                      (type_(0), type_(0), type_(1)), np.float64(1e-12), np.float64(1e-12))
    e = create_experiment([body(velocity=V(0, 0, 0))],
                          Settings(1., integrator="dop853"), rotations=(r,))
    document = to_document(advance(e, 1))
    assert document["schema_version"] == 10
    assert to_document(from_document(document)) == document
    with pytest.raises(ValueError, match="Ветки не поддерживают"):
        branch_experiment(from_document(document))


@pytest.mark.parametrize("value", (True, False, np.bool_(True), np.bool_(False)))
@pytest.mark.parametrize("field", ("quaternion", "angular_momentum", "quaternion_atol", "momentum_atol"))
def test_rotation_state_rejects_bool_in_each_numeric_field(value, field):
    values = dict(body="A", figure=RigidFigure(1., (2.,)*3, 4.),
                  quaternion=(1., 0., 0., 0.), angular_momentum=(0., 0., 1.),
                  quaternion_atol=1e-12, momentum_atol=1e-12)
    if field in ("quaternion", "angular_momentum"):
        vector = list(values[field]); vector[0] = value
        values[field] = vector
    else:
        values[field] = value
    with pytest.raises(ValueError):
        RotationState(**values)


@pytest.mark.parametrize("dtype", (bool, object, complex))
def test_array_vector_paths_do_not_erase_bool_or_complex(dtype):
    values = np.array([True, 1, 1], dtype=dtype)
    with pytest.raises(ValueError):
        RigidFigure(1., values, 4.)
    q = np.array([True, 0, 0, 0], dtype=dtype)
    with pytest.raises(ValueError):
        rotation_matrix(q)


def test_temporal_numpy_arrays_do_not_turn_into_integer_moments():
    for unit in ('Y', 's'):
        with pytest.raises(ValueError):
            RigidFigure(1., np.array([1, 1, 1], dtype='timedelta64['+unit+']'), 4.)


@pytest.mark.parametrize("field", ("position", "velocity", "spin"))
def test_body_rejects_noncanonical_components_in_mutated_vectors(field):
    vector = V(0, 0, 0)
    vector.x = True
    with pytest.raises(ValueError):
        body(**{field: vector})


@pytest.mark.parametrize("field", ("dt", "restitution", "rtol", "position_atol", "velocity_atol"))
@pytest.mark.parametrize("value", (True, False, np.bool_(True), np.bool_(False)))
def test_settings_reject_bool_in_each_physical_scalar(field, value):
    with pytest.raises(ValueError):
        Settings(**(dict(dt=1.) | {field: value}))


@pytest.mark.parametrize("value", (True, False, np.bool_(True), np.bool_(False), float("nan"), float("inf")))
def test_public_scalar_operations_reject_before_consuming_invalid_types(value):
    from solar_simulator.contacts import first_contact, run_until_contact
    from solar_simulator.collisions import simulate_collisions
    from solar_simulator.impacts import resolve_contact
    from solar_simulator.scenarios import circular_pair
    touching = [body(position=V(-1, 0, 0), radius=1.),
                body(name='B', position=V(1, 0, 0), velocity=V(-1, 0, 0), radius=1.)]
    calls = [lambda: V(1, 2, 3).multiply(value), lambda: V(1, 2, 3).divide(value),
             lambda: V(1, 2, 3).rotate_2d(value), lambda: step([body()], value),
             lambda: sun_earth(value), lambda: first_contact([body()], value),
             lambda: run_until_contact([body()], value, 0),
             lambda: simulate_collisions([body()], 1., 0, restitution=value),
             lambda: resolve_contact(touching, 0, 1, value),
             lambda: circular_pair("A", value, "B", 1., 10.),
             lambda: circular_pair("A", 1., "B", value, 10.),
             lambda: circular_pair("A", 1., "B", 1., value),
             lambda: pair_field(RigidFigure(1., (2.,)*3, 4.), value, (10., 0., 0.), (1., 0., 0., 0.))]
    for call in calls:
        with pytest.raises(ValueError):
            call()
    for index in range(3):
        arguments = [1., 1., 1.]; arguments[index] = value
        with pytest.raises(ValueError):
            V.circular_position(*arguments)


def test_numpy_conversion_is_exact_and_builtin_values_retain_their_types():
    for value in (0, 2**53+1, -0.0, 1e-300, 1e300):
        v = V(value, 0, 0)
        assert type(v.x) is type(value) and v.x == value
        if type(value) is float:
            assert v.x.hex() == value.hex()
    for type_ in (np.float16, np.float32, np.float64):
        value = type_(-0.0)
        assert V(value, 0, 0).x.hex() == float(value).hex()
        value = type_(1.125)
        assert V(value, 0, 0).x.hex() == float(value).hex()
    value = np.uint64(2**64-1)
    assert type(body(mass=value).mass) is int
    assert body(mass=value).mass == 2**64-1


def test_extended_numpy_float_is_rejected_only_when_wider_than_float64():
    value = np.longdouble(1)
    if value.dtype.itemsize > 8:
        for call in (lambda: V(value, 0, 0), lambda: body(mass=value),
                     lambda: RigidFigure(1., np.array([2, 2, 2], dtype=np.longdouble), 4.)):
            with pytest.raises(ValueError):
                call()
    else:
        assert V(value, 0, 0).x == 1.


def test_codec_stays_strict_and_accepts_existing_builtin_documents():
    document = to_document(create_experiment([body()], Settings(1.)))
    assert to_document(from_document(document)) == document
    for value in (True, np.float64(1), float("nan"), float("inf")):
        from copy import deepcopy
        invalid = deepcopy(document); invalid["bodies"][0]["mass"] = value
        with pytest.raises(ValueError):
            from_document(invalid)


@pytest.mark.parametrize("value", (True, False, np.bool_(True), np.bool_(False)))
@pytest.mark.parametrize("field", ("times", "rtol", "atol", "max_step"))
def test_model_solver_controls_reject_bool_without_changing_solver(field, value):
    from solar_simulator.rotation import integrate
    controls = dict(times=[0., 1.], rtol=1e-11, atol=1e-12, max_step=np.inf)
    controls[field] = [0., value] if field == 'times' else value
    with pytest.raises(ValueError):
        integrate(RigidFigure(1., (2.,)*3, 4.), [1., 0., 0., 0., 0., 0., 0.],
                  controls.pop('times'), **controls)


def test_nbody_time_grid_and_step_bound_reject_bool_and_keep_infinite_ceiling():
    from solar_simulator.nbody_rotation import integrate
    f = RigidFigure(1., (2.,)*3, 4.)
    r = RotationState('A', f, (1., 0., 0., 0.), (0., 0., 0.), 1e-12, 1e-12)
    for value in (True, False, np.bool_(True), np.bool_(False)):
        with pytest.raises(ValueError):
            integrate([body()], (r,), [0., value])
        with pytest.raises(ValueError):
            integrate([body()], (r,), [0., 1.], max_step=value)
    assert len(integrate([body()], (r,), [0., 1.], max_step=np.float64('inf'))) == 2


def test_legacy_schema1_migration_continuation_and_branch_remain_supported():
    import json
    legacy = json.loads('''{
      "schema_version": 1, "units": "SI", "model": "newtonian-verlet",
      "settings": {"dt": 1.0, "backend": "python", "contact_mode": "stop", "restitution": 1.0},
      "initial": [{"name": "A", "mass": 1.0, "radius": 0.0,
                   "position": [0, 0, 0], "velocity": [1, 0, 0]}],
      "bodies": [{"name": "A", "mass": 1.0, "radius": 0.0,
                  "position": [2.0, 0, 0], "velocity": [1, 0, 0]}],
      "time": 2.0, "dissipated_energy": 0.0, "halted": false, "events": []
    }''')
    loaded = from_document(legacy)
    assert loaded.settings.error_control == 'global-rms'
    current = to_document(advance(loaded, 1))
    assert current['schema_version'] == 9
    assert current['bodies'][0]['position'][0] == 3.
    assert branch_experiment(from_document(current)).parent.time == 3.


def test_existing_public_schema9_checkpoint_roundtrip_preserves_values_and_input_bytes():
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parents[1]/'docs/solar-sandbox-strict-checkpoint.json'
    raw = path.read_bytes(); document = json.loads(raw)
    assert document['schema_version'] == 9
    assert to_document(from_document(document)) == document
    assert path.read_bytes() == raw


@pytest.mark.parametrize('field', ('dt', 'restitution', 'rtol', 'position_atol', 'velocity_atol'))
@pytest.mark.parametrize('type_', (np.float64, np.float32, np.bool_))
def test_codec_numeric_settings_stay_builtin_only_despite_constructor_normalization(field, type_):
    document = to_document(create_experiment([body()], Settings(1.)))
    document['settings'][field] = type_(document['settings'][field])
    with pytest.raises(ValueError, match='число в контрольной точке'):
        from_document(document)
