"""Bad provenance refuses before any scientific imports or propagation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

def test_wrong_current_manifest_pin_fails_early(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'scripts/recompute_current040_419.py'
    spec = importlib.util.spec_from_file_location('current419', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    p = tmp_path / 'verification-current040/manifest-v1.json'; p.parent.mkdir()
    p.write_text('{}')
    with pytest.raises(ValueError, match='manifest SHA mismatch'):
        module.preflight(tmp_path, '0' * 64)
    with pytest.raises((ValueError, KeyError)):
        module.preflight(tmp_path, hashlib.sha256(p.read_bytes()).hexdigest())
