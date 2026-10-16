import numpy as np
import pytest
from matplotlib.figure import Figure

from solar_simulator.orbit_view import trajectory_data,draw_orbits


@pytest.mark.parametrize('axes,expected', [((0,1),[[-2,-4],[-3,-6]]),
                                         ((0,2),[[-2,-6],[-3,-9]]),
                                         ((1,2),[[-4,-6],[-6,-9]])])
def test_relative_projections_retain_every_snapshot_and_current_marker(axes,expected):
    frames=[dict(A=(1,2,3),B=(3,6,9)),dict(A=(2,4,6),B=(5,10,15))]
    names,paths,markers=trajectory_data(frames,['A'],'B',axes)
    assert names==['A']
    np.testing.assert_array_equal(paths[0],expected)
    np.testing.assert_array_equal(markers,[expected[-1]])


def test_missing_premerge_names_and_missing_reference_do_not_mix_tracks():
    frames=[dict(A=(1,2,3),B=(3,6,9)),dict(Merged=(8,9,10)),dict(Merged=(11,12,13))]
    names,paths,markers=trajectory_data(frames,['Merged'],None,(0,1))
    assert names==['Merged']
    np.testing.assert_array_equal(paths[0],[[8,9],[11,12]])
    assert trajectory_data(frames,['Merged'],'B',(0,1))[0]==[]


def test_large_scene_has_bounded_artists_but_all_paths_and_named_reference():
    names=[f'body-{i}' for i in range(354)]
    frames=[{name:(i+k,2*i+k,3*i+k) for i,name in enumerate(names)} for k in range(10)]
    axis=Figure().add_subplot()
    visible,paths,markers=draw_orbits(axis,frames,names,'body-200',(0,1))
    assert visible==names and len(paths)==354 and markers.shape==(354,2)
    assert len(axis.lines)==0 and len(axis.collections)==2
    assert len(axis.collections[0].get_segments())==354
    assert len(axis.collections[1].get_offsets())==354
    np.testing.assert_array_equal(paths[0],[[-200,-400]]*10)
    assert [item.get_text() for item in axis.get_legend().get_texts()]==names[:12]+['body-200']
    assert axis.dataLim.x0<=-200 and axis.dataLim.x1>=153


def test_history_limit_keeps_all_1500_retained_snapshots_without_thinning():
    from collections import deque
    frames=deque((dict(A=(k,k+1,k+2)) for k in range(1502)),maxlen=1500)
    _,paths,markers=trajectory_data(frames,['A'],None,(0,2))
    assert paths[0].shape==(1500,2)
    np.testing.assert_array_equal(paths[0][0],[2,4])
    np.testing.assert_array_equal(markers,[[1501,1503]])
