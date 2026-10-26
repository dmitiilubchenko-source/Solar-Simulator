"""Exact pre373 sources independently check unchanged arithmetic and encodings."""
import hashlib
import struct
import sys
from pathlib import Path
from types import ModuleType
from zipfile import ZipFile

import numpy as np
import pytest

from solar_simulator import simulation, rotation
from solar_simulator.vector3 import Vector3

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'scripts/validation/numeric-before373.zip'
ARCHIVE_SHA = '0cbe5a3754c7732ac645d03c9a582b1193b9ec64475b6138974eff9fd2758abb'


@pytest.fixture
def before(monkeypatch):
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == ARCHIVE_SHA
    prefix = '_solar_numeric_before373'
    package = ModuleType(prefix); package.__path__ = []
    monkeypatch.setitem(sys.modules, prefix, package)
    with ZipFile(ARCHIVE) as archive:
        for name in ('vector3', 'simulation', 'rotation'):
            module = ModuleType(prefix+'.'+name); module.__package__ = prefix
            monkeypatch.setitem(sys.modules, module.__name__, module)
            raw = archive.read(f'src/solar_simulator/{name}.py')
            exec(compile(raw, str(ARCHIVE)+'/'+name+'.py', 'exec'), module.__dict__)
            setattr(package, name, module)
    return package


def body_bits(bodies):
    return [(b.name, tuple(struct.pack('!d', float(v)) for v in (
        b.mass, b.radius, b.position.x, b.position.y, b.position.z,
        b.velocity.x, b.velocity.y, b.velocity.z, b.spin.x, b.spin.y, b.spin.z)))
            for b in bodies]


@pytest.mark.parametrize('eccentricity', (0., .2, .8))
def test_builtin_verlet_trajectory_matches_exact_pre373_sources(before, eccentricity):
    old, period = before.simulation.sun_earth(eccentricity)
    new, current_period = simulation.sun_earth(eccentricity)
    assert struct.pack('!d', period) == struct.pack('!d', current_period)
    dt = period/4000
    for _ in range(128):
        old = before.simulation.step(old, dt)
        new = simulation.step(new, dt)
    assert body_bits(new) == body_bits(old)
    assert simulation.total_energy(new).hex() == before.simulation.total_energy(old).hex()


def test_builtin_rotational_field_and_solution_preserve_pre373_bits(before):
    old = before.rotation.RigidFigure(1e15, (2e20, 2.5e20, 3e20), 1000.)
    new = rotation.RigidFigure(1e15, (2e20, 2.5e20, 3e20), 1000.)
    args = (2e14, (12000., 3000., -800.), (1., 0., 0., 0.))
    a = before.rotation.pair_field(old, *args); b = rotation.pair_field(new, *args)
    assert a[0].hex() == b[0].hex()
    assert np.array_equal(a[1].view(np.uint64), b[1].view(np.uint64))
    assert np.array_equal(a[2].view(np.uint64), b[2].view(np.uint64))
    initial = [1., 0., 0., 0., 1e16, -2e16, 3e16]
    times = np.linspace(0., 1000., 9)
    a = before.rotation.integrate(old, initial, times)
    b = rotation.integrate(new, initial, times)
    assert np.array_equal(a.view(np.uint64), b.view(np.uint64))


def test_existing_builtin_vector_operations_preserve_pre373_bits(before):
    for value in ((1, 2, 3), (-0., .125, 1e-100), (1e100, -2e100, 3e100)):
        old = before.vector3.Vector3(*value)
        new = Vector3(*value)
        for method, argument in (('multiply', .75), ('divide', 3.), ('rotate_2d', .2)):
            a, b = getattr(old, method)(argument), getattr(new, method)(argument)
            assert [float(v).hex() for v in vars(a).values()] == [float(v).hex() for v in vars(b).values()]
        assert old.normalize().x.hex() == new.normalize().x.hex()


def test_numeric_history_is_explicit_and_never_authorizes_live_source(tmp_path):
    from scripts.release_history import NUMERIC_ARCHIVE, ui_historical_sha
    from scripts.fixed_j2_year import verify
    name = 'src/solar_simulator/simulation.py'
    target = tmp_path/NUMERIC_ARCHIVE; target.parent.mkdir(parents=True)
    target.write_bytes(ARCHIVE.read_bytes())
    with ZipFile(target) as z:
        expected = hashlib.sha256(z.read(name)).hexdigest()
    live = tmp_path/name; live.parent.mkdir(parents=True); live.write_bytes(b'new runtime')
    assert ui_historical_sha(tmp_path, name, expected) == expected
    verify({name: expected}, tmp_path, historical=True)
    with pytest.raises(ValueError, match='SHA mismatch'):
        verify({name: expected}, tmp_path)
    with pytest.raises(ValueError, match='SHA mismatch'):
        from scripts.ias15_process import verify_files
        verify_files({name: expected}, root=tmp_path)
    assert live.read_bytes() == b'new runtime'


@pytest.mark.parametrize('damage', ('bytes', 'missing', 'wrong-sha', 'escape'))
def test_numeric_history_rejects_missing_corrupted_and_unbound_sources(tmp_path, damage):
    from scripts.release_history import NUMERIC_ARCHIVE, ui_historical_sha
    name = 'src/solar_simulator/simulation.py'
    archive = tmp_path/NUMERIC_ARCHIVE; archive.parent.mkdir(parents=True)
    archive.write_bytes(ARCHIVE.read_bytes())
    with ZipFile(archive) as z:
        expected = hashlib.sha256(z.read(name)).hexdigest()
    live = tmp_path/name; live.parent.mkdir(parents=True); live.write_bytes(b'new runtime')
    if damage == 'bytes':
        archive.write_bytes(archive.read_bytes()+b'changed')
        with pytest.raises(ValueError, match='archive'):
            ui_historical_sha(tmp_path, name, expected)
    elif damage == 'escape':
        with pytest.raises(ValueError, match='escapes'):
            ui_historical_sha(tmp_path, '../escape.py', expected)
    else:
        if damage == 'missing':archive.unlink()
        else:expected = '0'*64
        assert ui_historical_sha(tmp_path, name, expected) != expected
