from concurrent.futures import CancelledError
from threading import Event

import pytest


def _record(tmp_path):
    from solar_simulator.experiment import Settings,create_experiment
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    from solar_simulator.trajectory import record_trajectory
    seed=create_experiment([Body('probe',1.,Vector3(1,2,3),Vector3(2,3,4))],Settings(1.))
    directory=tmp_path/'track';record_trajectory(seed,directory,10.,packet_steps=1)
    return directory


@pytest.mark.parametrize('phase',['Проверка файлов','Подготовка просмотра'])
def test_cancel_between_frames_preserves_the_entire_recording(tmp_path,phase):
    from solar_simulator.trajectory_loader import prepare_trajectory
    directory=_record(tmp_path);before={p.name:p.read_bytes() for p in directory.iterdir()}
    stop=Event();seen=[]
    def progress(name,done,total):
        seen.append((name,done,total))
        if name==phase and done==2:stop.set()
    with pytest.raises(CancelledError):prepare_trajectory(directory,stop.is_set,progress)
    assert seen[-1]==(phase,2,11)
    assert before=={p.name:p.read_bytes() for p in directory.iterdir()}


def _check_background_loading_and_cancellation(tmp_path):
    from threading import get_ident
    from unittest.mock import patch
    import tkinter as tk
    from solar_simulator.app import Laboratory
    from solar_simulator.storage import to_document
    from solar_simulator.trajectory_loader import prepare_trajectory,TrajectoryLoader
    directory=_record(tmp_path)
    root=tk.Tk();root.withdraw();app=Laboratory(root)
    before=to_document(app.experiment);main_thread=get_ident()
    loader=None
    try:
        for cancel in (False,True):
            entered=Event();release=Event();threads=[]
            def held(*args):
                threads.append(get_ident());entered.set()
                assert release.wait(10)
                return prepare_trajectory(*args)
            with patch('solar_simulator.trajectory_loader.prepare_trajectory',side_effect=held):
                loader=TrajectoryLoader(tk.Toplevel(root),directory)
                assert entered.wait(5)
                heartbeat=[];root.after(0,lambda:heartbeat.append(get_ident()));root.update()
                assert heartbeat==[main_thread] and threads[0]!=main_thread
                assert not loader.future.done() and to_document(app.experiment)==before
                if cancel:loader.close()
                release.set()
                if cancel:
                    with pytest.raises(CancelledError):loader.future.result(timeout=10)
                    assert loader.viewer is None and loader.closed
                else:
                    loader.future.result(timeout=10);loader._poll();viewer=loader.viewer
                    assert viewer is not None and len(viewer.frames)==11
                    ids=(id(viewer._plot_artists.paths),id(viewer._plot_artists.markers))
                    for index in (1,5,10):
                        viewer.player.seek(index);viewer._draw()
                        assert ids==(id(viewer._plot_artists.paths),id(viewer._plot_artists.markers))
                        points=viewer._plot_artists.paths.get_segments()[0]
                        assert tuple(points[-1])==(1+2*index,2+3*index)
                        assert len(viewer.axis.collections)==2
                    viewer.close()
                assert to_document(app.experiment)==before
        entered=Event();release=Event()
        def held_on_close(*args):
            entered.set();assert release.wait(10)
            return prepare_trajectory(*args)
        with patch('solar_simulator.trajectory_loader.prepare_trajectory',side_effect=held_on_close):
            loader=TrajectoryLoader(tk.Toplevel(root),directory)
            assert entered.wait(5)
            app.close()
            assert loader.closed and loader.stop.is_set()
            release.set()
            with pytest.raises(CancelledError):loader.future.result(timeout=10)
    finally:
        if loader is not None and not loader.closed:loader.close()
        app.close()


def test_real_background_reader_keeps_tk_responsive_and_reuses_artists(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_background_loading_and_cancellation',tmp_path,source=__file__)
