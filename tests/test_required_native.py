"""A successful full native audit cannot hide import or skip failures."""
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_required_checker_fails_before_pytest_when_extension_is_missing():
    code = '''
import sys,importlib.abc
class Missing(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'solar_native': raise ModuleNotFoundError('controlled missing native')
sys.meta_path.insert(0,Missing())
from scripts.check_project import main
main(['--require-native'])
'''
    result = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-c', code],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode == 2 and 'solar_native' in result.stderr
    assert 'unrecognized arguments' not in result.stderr and 'TypeError' not in result.stderr
    assert 'passed' not in result.stdout


def test_native_probe_executes_real_extension():
    from scripts.native_audit import require_native
    assert require_native()['native_probe_passed']


def test_native_probe_rejects_python_substitute(monkeypatch):
    import sys
    from types import SimpleNamespace
    import pytest
    from scripts.native_audit import require_native
    monkeypatch.setitem(sys.modules, 'solar_native', SimpleNamespace(__file__='fake.py'))
    with pytest.raises(RuntimeError, match='extension'): require_native()


def test_strict_audit_rejects_runtime_and_collection_skips_but_default_allows_them(tmp_path):
    (tmp_path/'test_skip.py').write_text('import pytest\ndef test_optional(): pytest.skip("controlled")\n')
    (tmp_path/'test_collection_skip.py').write_text('import pytest\npytest.skip("controlled collection",allow_module_level=True)\n')
    (tmp_path/'test_pass.py').write_text('def test_real(): assert True\n')
    base = [sys.executable, '-X', 'utf8', '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', str(tmp_path)]
    for strict in (False, True):
        result = subprocess.run(base+(['-p', 'scripts.native_audit'] if strict else []), cwd=ROOT,
            capture_output=True, text=True, encoding='utf-8', timeout=30)
        assert result.returncode == (1 if strict else 0), result.stdout+result.stderr
        assert '2 skipped' in result.stdout
        if strict: assert 'Native audit rejected' in result.stdout
