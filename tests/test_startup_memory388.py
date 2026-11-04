"""Diagnostic contracts only; no orbit integrations or large allocations."""
import ast
import ctypes
import os
import subprocess
import sys
import pytest
from scripts.check_startup_memory388 import configure,THREAD_KEYS,unique_private,import_prefix,windows_memory,Counters


@pytest.mark.parametrize('profile,expected',[('cleared387',[None]*6),('blas1-only',[None,'1',None,None,None,None]),('all1-current',['1','1','1',None,None,None])])
def test_explicit_environment_is_diagnostic(profile,expected,monkeypatch):
    for key in THREAD_KEYS:monkeypatch.setenv(key,'99')
    assert list(configure(profile).values())==expected


def test_no_preparation_or_integration_can_enter_import_prefix():
    nodes=import_prefix('def prepare(root):\n import numpy as np\n from math import pi\n seeds=root.mkdir()\n integrate()\n')
    assert len(nodes)==2 and all(isinstance(n,(ast.Import,ast.ImportFrom)) for n in nodes)


def test_tree_unique_and_bytes_not_mib():
    rows=[dict(pid=1,create_time=1.,private=1024),dict(pid=2,create_time=2.,private=2048)]
    assert unique_private(rows)==3072
    with pytest.raises(ValueError):unique_private(rows+[rows[0]])


def test_unavailable_windows_api_is_explicit(monkeypatch):
    from types import SimpleNamespace
    from scripts import check_startup_memory388 as diagnostic
    monkeypatch.setattr(diagnostic,'os',SimpleNamespace(name='posix'))
    with pytest.raises(OSError,match='Windows API required'):diagnostic.windows_memory()
