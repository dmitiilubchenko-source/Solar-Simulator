import numpy as np
import pytest

from scripts.external_metric import Sources, potentials, weak_metric, leading_clock


def fixture():
    return Sources([3e12, 8e12], [[2e7, -4e7, 1e7], [-3e7, 1e7, 5e7]],
                   [[12., 23., -17.], [-4., 9., 11.]],
                   [[.002, -.003, .001], [.001, .004, -.002]], 2e5)


def independent_fields(x, time, sources):
    # Scalar definition, analytic continuation: no production gradient/metric.
    result = np.zeros(4, dtype=np.result_type(x, time, float))
    for gm, xs, vs, acc in zip(sources.gm, sources.positions, sources.velocities,
                               sources.accelerations):
        delta = x-(np.asarray(xs)+time*np.asarray(vs)+.5*time**2*np.asarray(acc))
        weight = gm/np.sqrt(delta@delta)
        result[0] += weight
        result[1:] += weight*(np.asarray(vs)+time*np.asarray(acc))
    return result


def test_potentials_and_metric_complex_step_moving_accelerating_sources():
    sources = fixture(); x = np.array([1e6, 2e6, -3e6]); f = potentials(x, sources)
    expected = independent_fields(x, 0., sources)
    assert np.allclose(np.r_[f.u, f.vector], expected, rtol=1e-14, atol=0.)
    derivatives = [independent_fields(x, 1j*1e-20, sources).imag/1e-20]
    derivatives += [independent_fields(x+1j*1e-20*axis, 0., sources).imag/1e-20
                    for axis in np.eye(3)]
    derivatives = np.array(derivatives)
    assert np.linalg.norm(np.c_[f.scalar_derivative, f.vector_derivative]-derivatives)/np.linalg.norm(derivatives) < 1e-11
    g, dg = weak_metric(x, sources)
    def metric(z, time):
        u, *ui = independent_fields(z, time, sources); c = sources.c
        out = np.eye(4, dtype=complex)*(1+2*u/c**2)
        out[0, 0] = -1+2*u/c**2
        out[0, 1:] = out[1:, 0] = -4*np.array(ui)/c**3
        return out
    assert np.linalg.norm(g-metric(x, 0.).real) < 1e-12
    expected_dg = [metric(x, 1j*1e-20/sources.c).imag/1e-20]
    expected_dg += [metric(x+1j*1e-20*axis, 0.).imag/1e-20 for axis in np.eye(3)]
    assert np.linalg.norm(dg-expected_dg)/np.linalg.norm(expected_dg) < 1e-11


def test_clock_material_derivative_and_translation_not_partial_derivative():
    sources = fixture(); x = np.array([1e6, 2e6, -3e6])
    v = np.array([31., -19., 14.]); a = np.array([.04, .01, -.03])
    rate, derivative = leading_clock(x, v, a, sources)
    time = 1j*1e-20
    u = independent_fields(x+v*time+.5*a*time**2, time, sources)[0]
    expected = 1-((v+a*time)@(v+a*time)/2+u)/sources.c**2
    assert rate == pytest.approx(expected.real, rel=1e-14)
    assert derivative == pytest.approx(expected.imag/1e-20, rel=1e-11)
    offset = np.array([1e9, -3e9, 2e9])
    translated = Sources(sources.gm, np.asarray(sources.positions)+offset,
                         sources.velocities, sources.accelerations, sources.c)
    assert np.allclose(leading_clock(x+offset, v, a, translated), [rate, derivative],
                       rtol=1e-12, atol=0.)
    f = potentials(x, sources)
    wrong = -(v@a+f.scalar_derivative[0])/sources.c**2
    assert abs((wrong-derivative)/derivative) > 1e-4


def test_empty_external_sources_flat_limit_and_defensive_copy():
    x = np.empty((0, 3)); sources = Sources([], x, x, x, 3e8)
    g, dg = weak_metric([1., 2., 3.], sources)
    assert np.array_equal(g, np.diag([-1., 1., 1., 1.]))
    assert not np.any(dg)
    assert leading_clock([0., 0., 0.], [0., 0., 0.], [0., 0., 0.], sources) == (1., 0.)
    gm = np.array([1.]); positions = np.array([[1., 0., 0.]])
    saved = Sources(gm, positions, [[0., 0., 0.]], [[0., 0., 0.]], 3e8)
    gm[0] = 100.; positions[0, 0] = 5.
    assert saved.gm == (1.,) and saved.positions == ((1., 0., 0.),)


@pytest.mark.parametrize('value', [True, '3e8', 0., -1., float('nan'), float('inf'), 1e308, 1e-300])
def test_invalid_c_rejected(value):
    with pytest.raises(ValueError):
        Sources([1.], [[1., 0., 0.]], [[0., 0., 0.]], [[0., 0., 0.]], value)


@pytest.mark.parametrize('kwargs', [dict(gm=[0.]), dict(gm=[-1.]), dict(gm=['1']),
                                   dict(velocities=[[2e8, 0., 0.]]),
                                   dict(accelerations=[[np.nan, 0., 0.]]),
                                   dict(positions=[[1., 2.]])])
def test_invalid_sources_rejected(kwargs):
    args = dict(gm=[1.], positions=[[1., 0., 0.]], velocities=[[0., 0., 0.]],
                accelerations=[[0., 0., 0.]], c=3e8); args.update(kwargs)
    with pytest.raises(ValueError):
        Sources(**args)


def test_coincidence_strong_field_fast_centre_and_overflow_rejected():
    sources = fixture()
    with pytest.raises(ValueError, match='Coincident'):
        potentials(sources.positions[0], sources)
    heavy = Sources([1e20], [[1., 0., 0.]], [[0., 0., 0.]], [[0., 0., 0.]], 3e8)
    with pytest.raises(ValueError, match='potential'):
        potentials([0., 0., 0.], heavy)
    with pytest.raises(ValueError, match='speed'):
        leading_clock([0., 0., 0.], [1e8, 0., 0.], [0., 0., 0.], sources)
    with pytest.raises(ValueError, match='representable'):
        potentials([1e308, 1e308, 1e308], sources)
