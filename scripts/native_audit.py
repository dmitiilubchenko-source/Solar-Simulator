"""Required native preflight and a pytest plugin that rejects skipped checks."""
import importlib
from importlib.machinery import EXTENSION_SUFFIXES, ExtensionFileLoader
from pathlib import Path

import pytest


def require_native():
    try:
        native = importlib.import_module('solar_native')
    except ImportError as error:
        raise RuntimeError('solar_native required; run .venv/Scripts/python.exe scripts/build_native.py') from error
    compiled = getattr(native, 'solar_native', native)  # Maturin installs a Python re-export package.
    path = str(getattr(compiled, '__file__', ''))
    loader = getattr(getattr(compiled, '__spec__', None), 'loader', None)
    if not any(path.endswith(suffix) for suffix in EXTENSION_SUFFIXES) or not isinstance(loader, ExtensionFileLoader):
        raise RuntimeError('solar_native must be a compiled extension, not a Python substitute')
    required = ('evolve', 'diagnostics', 'point_acceleration', 'run_until_contact',
                'resolve_contact', 'simulate_collisions')
    if any(not callable(getattr(compiled, name, None))
           or getattr(native, name, None) is not getattr(compiled, name, None) for name in required):
        raise RuntimeError('solar_native API incomplete; rebuild with scripts/build_native.py')
    positions, velocities = native.evolve([1.], [[0., 0., 0.]], [[2., -3., 4.]], .25, 2)
    if positions != [[1., -1.5, 2.]] or velocities != [[2., -3., 4.]]:
        raise RuntimeError('solar_native ballistic probe failed')
    return dict(native_probe_passed=True, extension=str(Path(path).resolve()))


def pytest_sessionstart(session):
    try:
        require_native()
    except RuntimeError as error:
        raise pytest.UsageError(str(error)) from error
    _skips.clear()


def pytest_collectreport(report):
    if report.skipped:
        _record_skip(report)


def pytest_runtest_logreport(report):
    if report.skipped:
        _record_skip(report)


# Reports do not contain config; plugin state is scoped to this pytest process.
_skips = []


def _record_skip(report):
    _skips.append(report.nodeid)


def pytest_sessionfinish(session, exitstatus):
    if _skips and exitstatus == 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter):
    if _skips:
        terminalreporter.write_sep('=', f'Native audit rejected: {len(_skips)} skipped checks', red=True)
        for nodeid in _skips:
            terminalreporter.write_line(nodeid)
