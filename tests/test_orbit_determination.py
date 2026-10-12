"""Analytic orbit oracle, separation controls, geometry and input contracts."""
from dataclasses import replace
from datetime import datetime, timedelta
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import brentq

from solar_simulator.orbit_determination import (OpticalObservation, EphemerisBackground,
    AU_METRES, LIGHT_AU_DAY, ARCSEC_PER_RADIAN, angular_residuals, predict_directions,
    propagate, fit_orbit, initial_states, decode_dataset, fit_dataset, evaluate_predictions)

ROOT = Path(__file__).resolve().parents[1]
MU = .0002959122082855911


def analytic_state(t):
    """Eccentric Kepler orbit, independent of the numerical force/integrator."""
    a, eccentricity = 2.3, .17
    mean = .4+np.sqrt(MU/a**3)*t
    anomaly = brentq(lambda e:e-eccentricity*np.sin(e)-mean, mean-eccentricity, mean+eccentricity, xtol=1e-14)
    speed = np.sqrt(MU/a**3)/(1-eccentricity*np.cos(anomaly))
    r = a*np.array([np.cos(anomaly)-eccentricity, np.sqrt(1-eccentricity**2)*np.sin(anomaly), 0.])
    v = a*speed*np.array([-np.sin(anomaly), np.sqrt(1-eccentricity**2)*np.cos(anomaly), 0.])
    rot = np.array([[1,0,0],[0,np.cos(.3),-np.sin(.3)],[0,np.sin(.3),np.cos(.3)]])
    return np.r_[rot@r, rot@v]


def synthetic_case():
    times = np.linspace(-100, 180, 30)
    zero = np.zeros((len(times),1,3))
    background = EphemerisBackground(times, ['Sun'], [MU], zero, zero)
    observations = []
    for index, t in enumerate(np.r_[np.linspace(-55, 30, 14), [45,60,90,120]]):
        # Known observer follows an independently generated circular orbit.
        observer = np.array([np.cos(1.5+np.sqrt(MU)*t), np.sin(1.5+np.sqrt(MU)*t), 0])
        emission = brentq(lambda s:s-t+np.linalg.norm(analytic_state(s)[:3]-observer)/LIGHT_AU_DAY,
                         t-.1, t, xtol=1e-13)
        direction = analytic_state(emission)[:3]-observer
        direction /= np.linalg.norm(direction)
        ra = np.rad2deg(np.arctan2(direction[1],direction[0]))%360
        dec = np.rad2deg(np.arcsin(direction[2]))
        night = (datetime(2020,3,1)+timedelta(days=float(t))).strftime('%Y-%m-%d')
        observations.append(OpticalObservation(str(index),night,float(t),ra,dec,.2,.3,tuple(observer),.2))
    return tuple(observations[:14]),tuple(observations[14:]),background


def test_analytic_eccentric_orbit_and_retarded_direction():
    training, holdout, background = synthetic_case()
    prediction = predict_directions(analytic_state(0),training+holdout,background)
    assert abs(angular_residuals(prediction,training+holdout)).max() < 2e-7
    epochs = np.array([-60,0,60,120])
    numerical = propagate(analytic_state(0),background,epochs)(epochs)
    truth = np.array([analytic_state(t) for t in epochs])
    assert np.linalg.norm(numerical[:,:3]-truth[:,:3],axis=1).max()*AU_METRES < .15
    # Reception-time target is demonstrably wrong by tens of arcseconds.
    simultaneous = np.array([analytic_state(o.time_days)[:3]-o.observer_position_au for o in training])
    simultaneous /= np.linalg.norm(simultaneous,axis=1)[:,None]
    assert np.linalg.norm(angular_residuals(simultaneous,training),axis=1).max() > 5


def test_recovers_six_parameters_and_predicts_unseen_analytic_positions():
    training, holdout, background = synthetic_case()
    rough = analytic_state(0)+np.array([.03,-.02,.01,.0002,-.0001,.0001])
    fit = fit_orbit(training,background,seeds=[rough])
    assert fit['rank'] == 6 and fit['covariance_au_day'] is not None
    assert fit['training_rms_arcsec'] < 1e-6
    assert evaluate_predictions(fit,holdout,background)['rms_arcsec'] < 2e-6
    assert np.linalg.norm(np.array(fit['state_au_day'])[:3]-analytic_state(0)[:3])*AU_METRES < 2
    covariance = np.array(fit['covariance_au_day'])
    assert np.allclose(covariance,covariance.T,atol=1e-18)
    assert np.linalg.eigvalsh(covariance).min() > 0


def test_training_only_range_initialization_recovers_analytic_orbit():
    training, holdout, background = synthetic_case()
    states = initial_states(training,background,ranges_au=[1.5,2.5])
    fit = fit_orbit(training,background,seeds=states)
    assert evaluate_predictions(fit,holdout,background)['rms_arcsec'] < 2e-6


def test_direction_wrap_pole_and_correlated_covariance():
    obs = OpticalObservation('a','2020-01-01',0,359.9999,0,.2,.3,(0,0,0),.4)
    angle = np.deg2rad(.0001)
    predicted = np.array([[np.cos(angle),np.sin(angle),0]])
    raw = angular_residuals(predicted,[obs])
    assert raw[0,0] == pytest.approx(.72,abs=1e-8)
    assert abs(raw[0,1]) < 1e-15
    weighted = angular_residuals(predicted,[obs],True).ravel()
    cov = np.array([[.2**2,.4*.2*.3],[.4*.2*.3,.3**2]])
    assert weighted@weighted == pytest.approx(raw.ravel()@np.linalg.solve(cov,raw.ravel()))
    pole = replace(obs,ra_deg=20.,dec_deg=90.)
    assert np.linalg.norm(angular_residuals([[0,0,1]],[pole])) < 1e-10


@pytest.mark.parametrize('field,value', [('time_days',float('nan')),('ra_deg',360),('dec_deg',91),
    ('sigma_ra_arcsec',0),('sigma_dec_arcsec',-1),('correlation',1),('ra_deg',True),
    ('observer_position_au',(0,0,float('inf'))),('night','2020-1-1')])
def test_rejects_invalid_observation(field,value):
    training, _, _ = synthetic_case()
    with pytest.raises(ValueError):
        replace(training[0],**{field:value})


def test_no_background_or_dense_output_extrapolation():
    _, _, background = synthetic_case()
    with pytest.raises(ValueError,match='coverage'):
        background.positions(-100.01)
    orbit = propagate(analytic_state(0),background,[-10,10])
    with pytest.raises(ValueError,match='integrated'):
        orbit([10.01])


def test_short_arc_and_duplicate_training_rejected():
    train, _, background = synthetic_case()
    with pytest.raises(ValueError,match='distinct'):
        fit_orbit([train[0]]*4,background)
    short = tuple(replace(o,time_days=float(i)/10,night='2020-01-01') for i,o in enumerate(train[:4]))
    with pytest.raises(ValueError,match='Insufficient'):
        fit_orbit(short,background,seeds=[analytic_state(0)])


def test_nonconverged_fit_is_not_a_success():
    train, _, background = synthetic_case()
    with pytest.raises(RuntimeError,match='converged'):
        fit_orbit(train,background,seeds=[analytic_state(0)+[.1,0,0,.001,0,0]],max_evaluations=1)


def real_document():
    return json.loads((ROOT/'src/solar_simulator/data/orbit-observations-13270.json').read_text(encoding='utf-8'))


def test_frozen_real_case_has_no_target_trajectory_and_no_night_leakage():
    document = real_document()
    training, holdout, background = decode_dataset(document)
    assert len(training) == 59 and len(holdout) == 24
    assert len(background.names) == 11
    assert not any('13270' in name for name in background.names)
    assert max(o.time_days for o in training) < min(o.time_days for o in holdout)
    assert not {o.night for o in training} & {o.night for o in holdout}
    assert all(r['sigma_source']=='MPC ADES rmsRA/rmsDec' for r in document['observations'])


@pytest.mark.parametrize('mutate', [
    lambda d:d.update(frame='Ecliptic J2000'),
    lambda d:d.update(time_scale='UTC'),
    lambda d:d['observations'][-1].update(id=d['observations'][0]['id']),
    lambda d:d['observations'][-1].update(split='train'),
    lambda d:d['observations'][-1].update(night=d['observations'][0]['night']),
])
def test_rejects_frame_and_split_leakage(mutate):
    document = real_document()
    mutate(document)
    with pytest.raises(ValueError):
        decode_dataset(document)


def test_pipeline_passes_no_holdout_to_optimizer(monkeypatch,tmp_path):
    import solar_simulator.orbit_determination as module
    doc = real_document()
    path = tmp_path/'dataset.json'
    path.write_text(json.dumps(doc),encoding='utf-8')
    captured = []
    def spy(training,background,**kwargs):
        captured.extend(o.id for o in training)
        return {'state_au_day':initial_states(training,background)[0].tolist()}
    monkeypatch.setattr(module,'fit_orbit',spy)
    monkeypatch.setattr(module,'evaluate_predictions',lambda *a,**k:{'rms_arcsec':0})
    result = fit_dataset(path,tmp_path/'report.json')
    assert set(captured) == {r['id'] for r in doc['observations'] if r['split']=='train'}
    assert set(captured).isdisjoint({r['id'] for r in doc['observations'] if r['split']=='holdout'})
    assert len(result['dataset_sha256']) == 64


def test_radial_geometry_reports_missing_information_instead_of_fake_covariance():
    _, _, background = synthetic_case()
    training = tuple(OpticalObservation(str(i),f'2020-01-{i+1:02d}',float(t),0,0,.2,.2,(0,0,0))
        for i,t in enumerate([-3,-1,1,3]))
    fit = fit_orbit(training,background,seeds=[[2,0,0,.001,0,0]])
    assert fit['rank'] < 6 and not fit['identifiable_locally']
    assert fit['covariance_au_day'] is None
    from solar_simulator.orbit_determination import prediction_uncertainty
    assert prediction_uncertainty(fit,training,background) is None


def test_noisy_analytic_data_and_prediction_uncertainty():
    training,holdout,background = synthetic_case()
    rng = np.random.default_rng(68431)
    noisy = []
    for o in training:
        east,north = rng.multivariate_normal([0,0],[[.04,.012],[.012,.09]])
        noisy.append(replace(o,ra_deg=(o.ra_deg+east/(3600*np.cos(np.deg2rad(o.dec_deg))))%360,
                             dec_deg=o.dec_deg+north/3600))
    fit = fit_orbit(noisy,background,seeds=[analytic_state(0)+[.02,0,0,.0001,0,0]])
    assert .25 < fit['reduced_chi_square'] < 2.5
    assert evaluate_predictions(fit,holdout,background)['rms_arcsec'] < 2
    from solar_simulator.orbit_determination import prediction_uncertainty
    uncertainty = prediction_uncertainty(fit,holdout,background)
    assert len(uncertainty['predictions']) == len(holdout)
    assert all(p['major_sigma_arcsec'] >= p['minor_sigma_arcsec'] > 0 for p in uncertainty['predictions'])
    assert uncertainty['epoch_position_sigma_trace_metres'] > 1


def test_cli_real_fit_and_failure_contract(tmp_path,capsys):
    from solar_simulator.cli import main
    path = ROOT/'src/solar_simulator/data/orbit-observations-13270.json'
    output = tmp_path/'fit.json'
    assert main(['fit-orbit',str(path),str(output)]) == 0
    result = json.loads(output.read_text(encoding='utf-8'))
    assert result['fit']['rank'] == 6
    assert result['training']['rms_arcsec'] < .4
    assert result['holdout']['rms_arcsec'] < .8
    assert result['holdout']['count'] == 24
    assert len(result['fit']['attempts']) == 4
    with pytest.raises(SystemExit) as caught:
        main(['fit-orbit',str(path),str(path)])
    assert caught.value.code == 2


def test_observation_loader_selection_and_time_conversion():
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from fetch_orbit_observations import select_observations,utc_jd,vector_rows
    assert utc_jd('2000-01-01T12:00:00Z') == 2451545.
    record = dict(permid='13270',stn='T08',obstime='2020-02-01T00:00:00Z',
        Obstype='optical',mode='CCD',astcat='Gaia2',subfrm=None,deprecated=None,
        rmsra='0.2',rmsdec='0.3')
    samples = [dict(record,obsid=str(i),obstime=f'2020-02-{i+1:02d}T00:00:00Z') for i in range(10)]
    assert len(select_observations(samples+[dict(record,obsid='b',subfrm='B1950.0')])) == 10
    with pytest.raises(ValueError):
        select_observations(samples+[samples[0]])
    with pytest.raises(ValueError):
        vector_rows({'error':'bad'},0,'T08@399',[2451545.],time_type='UT',delta=True)
