"""Regressions at the boundary between mutable state and reproducible starts."""
from dataclasses import replace
import subprocess
import sys

import pytest

from solar_simulator.experiment import advance, preset
from solar_simulator.storage import from_document, to_document


@pytest.mark.parametrize("field", ["position", "velocity", "spin"])
@pytest.mark.parametrize("operation", ["save", "advance"])
def test_changed_zero_time_state_requires_new_experiment(field, operation):
    experiment = preset("sun-earth")
    getattr(experiment.bodies[0], field).x += 1
    with pytest.raises(ValueError, match="исходн"):
        (to_document(experiment) if operation == "save" else advance(experiment, 1))


def test_loading_inconsistent_zero_time_document_is_rejected():
    document = to_document(preset("sun-earth"))
    document["bodies"][0]["velocity"][0] += 1
    with pytest.raises(ValueError, match="исходн"):
        from_document(document)


def test_explicit_zero_time_contact_remains_supported():
    experiment = preset("spheres")
    experiment = replace(experiment, settings=replace(experiment.settings, contact_mode="stop"))
    result = advance(experiment, 2000)
    assert to_document(from_document(to_document(result))) == to_document(result)


def test_user_system_does_not_read_optional_catalogs_in_fresh_process():
    code = '''
from pathlib import Path
original = Path.read_bytes
def deny(path):
    if path.name in ("asteroids-catalog-20261008.json", "kuiper-20261010.json", "kuiper-ring.json"):
        raise FileNotFoundError("Optional catalog unavailable")
    return original(path)
Path.read_bytes = deny
from solar_simulator.experiment import preset, advance
from solar_simulator.storage import to_document, from_document
p = preset("binary-star")
assert from_document(to_document(advance(p, 2))).time > 0
import sys
assert "solar_simulator.perturbers" not in sys.modules
assert "solar_simulator.kuiper_ring" not in sys.modules
'''
    result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
