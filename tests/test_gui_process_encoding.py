from types import SimpleNamespace

import pytest

from test_app_workflows import run_gui_check


def test_original_non_ascii_failure_survives_a_conflicting_parent_environment(tmp_path,monkeypatch):
    source=tmp_path/'child.py'
    source.write_text('def fail(path):\n    raise RuntimeError("Соберите Rust-модуль")\n',encoding='utf-8')
    monkeypatch.setenv('PYTHONIOENCODING','cp1251')
    monkeypatch.setenv('PYTHONUTF8','0')
    with pytest.raises(AssertionError,match='Соберите Rust-модуль') as error:
        run_gui_check('fail',tmp_path,source)
    assert 'RuntimeError' in str(error.value) and 'UnicodeDecodeError' not in str(error.value)


def test_missing_pipe_output_cannot_mask_the_process_exit(tmp_path,monkeypatch):
    monkeypatch.setattr('test_app_workflows.subprocess.run',lambda *a,**k:SimpleNamespace(returncode=9,stdout=None,stderr=None))
    with pytest.raises(AssertionError,match='GUI child exit 9'):
        run_gui_check('unused',tmp_path)
