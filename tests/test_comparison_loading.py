"""Cancellation, exact old results, and real Tk heartbeat at a held IO boundary."""
from concurrent.futures import CancelledError
import hashlib
from pathlib import Path
from threading import Event
from types import ModuleType
from zipfile import ZipFile

import pytest

from solar_simulator.comparison_loader import prepare_comparison
from solar_simulator.trajectory import Trajectory
from tests.test_comparison_gui import make_pair


@pytest.fixture(scope='module')
def recorded_pair(tmp_path_factory):
    directory=tmp_path_factory.mktemp('comparison-readonly')
    make_pair(directory)
    return directory


@pytest.mark.parametrize('side',['before','after'])
def test_background_preparation_matches_exact_032_results(recorded_pair,side):
    tmp_path=recorded_pair
    before={p:p.read_bytes() for p in tmp_path.rglob('*.json')}
    root=Path(__file__).resolve().parents[1]
    with ZipFile(root/'scripts/validation/release032-ui-sources.zip') as archive:
        source=archive.read('src/solar_simulator/comparison.py')
    import json
    expected=json.loads((root/'docs/release-032-validation.json').read_bytes())['source_sha256']
    assert hashlib.sha256(source).hexdigest()==expected['src/solar_simulator/comparison.py']
    old=ModuleType('solar_simulator._comparison032');old.__package__='solar_simulator'
    exec(compile(source,'archived-032-comparison.py','exec'),old.__dict__)
    previous=old.Comparison(Trajectory(tmp_path/'parent'),Trajectory(tmp_path/'child'),event_side=side)
    current,samples=prepare_comparison(tmp_path/'parent',tmp_path/'child',lambda:False,lambda *args:None,event_side=side)
    assert current.pairs==previous.pairs and current.times==previous.times
    assert samples==previous.report()['samples']
    for reference in (None,'free','missing'):
        assert current.report(reference=reference)==previous.report(reference=reference)
    assert before=={p:p.read_bytes() for p in tmp_path.rglob('*.json')}


@pytest.mark.parametrize('phase',['Чтение родителя','Чтение ветки','Состояния родителя',
    'Состояния ветки','Поиск родителя','Общие эпохи','Подготовка разностей'])
def test_cancel_in_each_preparation_phase_keeps_recordings(recorded_pair,phase):
    tmp_path=recorded_pair
    before={p:p.read_bytes() for p in tmp_path.rglob('*.json')}
    stop=Event();seen=[]
    def progress(name,done,total):
        seen.append((name,done))
        if name==phase and done==1:stop.set()
    with pytest.raises(CancelledError):
        prepare_comparison(tmp_path/'parent',tmp_path/'child',stop.is_set,progress,event_side='after')
    assert seen[-1]==(phase,1)
    assert before=={p:p.read_bytes() for p in tmp_path.rglob('*.json')}


def test_cancel_before_reading_does_not_need_valid_paths(tmp_path):
    with pytest.raises(CancelledError):
        prepare_comparison(tmp_path/'missing',tmp_path/'absent',lambda:True,lambda *args:None,event_side='after')
    assert not list(tmp_path.iterdir())


def _check_comparison_background(tmp_path):
    from threading import get_ident
    from unittest.mock import patch
    import tkinter as tk
    from solar_simulator.app import Laboratory
    from solar_simulator.comparison_loader import ComparisonLoader
    from solar_simulator.storage import to_document
    from solar_simulator.comparison_view import ComparisonViewer
    make_pair(tmp_path)
    before={p:p.read_bytes() for p in tmp_path.rglob('*.json')}
    root=tk.Tk();root.withdraw();app=Laboratory(root)
    main_thread=get_ident();original=to_document(app.experiment)
    loader=None
    try:
        for action in ('ready','cancel','destroy-parent'):
            entered=Event();release=Event();threads=[];view_threads=[]
            def held(*args,**kwargs):
                threads.append(get_ident());entered.set()
                assert release.wait(10)
                return prepare_comparison(*args,**kwargs)
            def view(*args,**kwargs):
                view_threads.append(get_ident())
                assert 'samples' in kwargs
                return ComparisonViewer(*args,**kwargs)
            with patch('solar_simulator.comparison_loader.prepare_comparison',side_effect=held), \
                 patch('solar_simulator.comparison_view.ComparisonViewer',side_effect=view):
                loader=ComparisonLoader(tk.Toplevel(root),tmp_path/'parent',tmp_path/'child',event_side='after')
                assert entered.wait(5)
                heartbeat=[];root.after(0,lambda:heartbeat.append(get_ident()));root.update()
                assert heartbeat==[main_thread] and threads==[threads[0]] and threads[0]!=main_thread
                assert not loader.future.done() and to_document(app.experiment)==original
                if action=='cancel':loader.close()
                elif action=='destroy-parent':app.close()
                release.set()
                if action=='ready':
                    loader.future.result(timeout=10);loader._poll()
                    assert view_threads==[main_thread] and loader.viewer is not None
                    assert len(loader.viewer.samples)==4
                    loader.viewer.close()
                else:
                    with pytest.raises(CancelledError):loader.future.result(timeout=10)
                    assert loader.closed and loader.viewer is None and not view_threads
            assert before=={p:p.read_bytes() for p in before}
    finally:
        if loader is not None and not loader.closed:loader.close()
        app.close()


def test_comparison_reader_keeps_tk_alive_and_cancels_without_late_view(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_comparison_background',tmp_path,source=__file__)


def test_cli_view_uses_the_same_background_loader(monkeypatch,tmp_path):
    from solar_simulator import comparison_view
    calls=[]
    class Window:
        def mainloop(self):calls.append('mainloop')
    window=Window()
    monkeypatch.setattr(comparison_view.tk,'Tk',lambda:window)
    monkeypatch.setattr('solar_simulator.comparison_loader.ComparisonLoader',
        lambda *args,**kwargs:calls.append((args,kwargs)))
    comparison_view.launch(tmp_path/'parent',tmp_path/'child',event_side='before')
    assert calls==[((window,tmp_path/'parent',tmp_path/'child'),{'event_side':'before'}),'mainloop']
