import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from solar_simulator.orbit_view import draw_orbits
from solar_simulator.plot_artists import PlotArtists


def figures():
    f=Figure(figsize=(10,6));FigureCanvasAgg(f)
    orbit,energy=f.subplots(2,1);orbit.set_aspect('equal',adjustable='datalim')
    return f,orbit,energy


@pytest.mark.parametrize('axes',[(0,1),(0,2),(1,2)])
def test_persistent_paths_markers_balance_and_limits_match_fresh_axes(axes):
    before,old_orbit,old_energy=figures();after,orbit,energy=figures()
    artists=PlotArtists(orbit,energy)
    # Independent values include a hidden reference, shrinking extent, merge and emptiness.
    cases=[([dict(A=(1,2,3),B=(3,6,9)),dict(A=(2,4,6),B=(5,10,15))],['A'],'B',[(1,2),(2,4)]),
           ([dict(A=(0,0,0),B=(1,1,1))],['A','B'],None,[(0,0)]),
           ([dict(A=(1,2,3)),dict(Merged=(8,9,10)),dict(Merged=(11,12,13))],['Merged'],None,[(2,3)]),
           ([dict(A=(1,2,3))],['A'],'missing',[]),([],[],None,[])]
    ids=(id(artists.paths),id(artists.markers),id(artists.balance))
    for frames,names,reference,energies in cases:
        old_orbit.clear();old_energy.clear();old_orbit.set_aspect('equal',adjustable='datalim')
        expected=draw_orbits(old_orbit,frames,names,reference,axes)
        old_energy.plot([p[0] for p in energies],[p[1] for p in energies],color='#b35c1e')
        actual=artists.update(frames,names,reference,axes,energies)
        before.canvas.draw();after.canvas.draw()
        assert actual[0]==expected[0]
        for a,b in zip(actual[1],expected[1]):np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(actual[2],expected[2])
        for ax,old in ((orbit,old_orbit),(energy,old_energy)):
            np.testing.assert_allclose(ax.get_xlim(),old.get_xlim(),rtol=1e-14,atol=1e-14)
            np.testing.assert_allclose(ax.get_ylim(),old.get_ylim(),rtol=1e-14,atol=1e-14)
        np.testing.assert_array_equal(artists.balance.get_xydata(),old_energy.lines[0].get_xydata())
        assert ids==(id(artists.paths),id(artists.markers),id(artists.balance))
        assert len(orbit.collections)==2 and len(energy.lines)==1
        old_legend=old_orbit.get_legend();legend=orbit.get_legend()
        assert (legend is None)==(old_legend is None)
        if legend:assert [t.get_text() for t in legend.get_texts()]==[t.get_text() for t in old_legend.get_texts()]
    # Expected relative signs, independently of the shared projection helper.
    result=artists.update(cases[0][0],['A'],'B',(0,2),[(1,2)])
    np.testing.assert_array_equal(result[1][0],[[-2,-6],[-3,-9]])


def test_artist_count_and_full_history_remain_bounded_with_large_membership():
    _,orbit,energy=figures();artists=PlotArtists(orbit,energy)
    names=[f'body-{i}' for i in range(354)]
    frames=[{name:(i+k,2*i+k,3*i+k) for i,name in enumerate(names)} for k in range(1500)]
    for _ in range(3):
        artists.update(frames,names,'body-200',(0,1),[(i,float(i)) for i in range(1500)])
        assert len(artists.paths.get_segments())==354 and len(artists.paths.get_segments()[0])==1500
        assert len(orbit.collections)==2 and len(energy.lines)==1
        assert [t.get_text() for t in orbit.get_legend().get_texts()]==names[:12]+['body-200']


def _check_gui_model_changes(tmp_path):
    import tkinter as tk
    from solar_simulator.app import Laboratory
    from solar_simulator.storage import to_document
    root=tk.Tk();root.withdraw();app=Laboratory(root)
    try:
        app._open_solar_sandbox();original=to_document(app.experiment)
        ids=(id(app._plot_artists.paths),id(app._plot_artists.balance))
        app.view.set('Земля и Луна');app.reference.set('Тело: Earth')
        for plane in ('XY','XZ','YZ'):
            app.plane.set(plane);app._draw();app.canvas.draw()
            assert to_document(app.experiment)==original
            assert len(app.orbit.get_legend().get_texts())==2
        app._open_lunar_rotation();assert 'жёсткое' in app.energy.get_title()
        app.scenario.set('sun-earth');app._select_scenario();app._new()
        assert app.energy.get_title()=='' and app.energy.get_ylabel()=='Остаток баланса, Дж'
        assert ids==(id(app._plot_artists.paths),id(app._plot_artists.balance))
        app._reset();app._draw();assert len(app.orbit.collections)==2 and len(app.energy.lines)==1
    finally:app.close()


def test_real_gui_reuses_artists_but_refreshes_projection_and_scientific_labels(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_gui_model_changes',tmp_path,__file__)
