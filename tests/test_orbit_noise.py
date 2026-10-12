"""Correlated-night GLS against independent matrix algebra and coverage experiments."""
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from solar_simulator.orbit_determination import (OpticalNoiseModel, measurement_covariance,
    OpticalObservation,angular_residuals,fit_orbit,prediction_coverage,decode_dataset)
from test_orbit_determination import synthetic_case,analytic_state

ROOT = Path(__file__).resolve().parents[1]


def test_gls_objective_matches_full_covariance_and_is_permutation_invariant():
    training,_,_ = synthetic_case()
    observations = [replace(training[i],id=str(i),station='T08',night='2020-01-01') for i in range(4)]
    observations.append(replace(training[4],id='4',station='T05',night='2020-01-01'))
    tau = .15
    residual = np.array([[.1,-.2],[-.2,.3],[.4,.1],[-.1,.5],[.1,.2]])
    noise = OpticalNoiseModel(observations,tau)
    covariance = np.zeros((10,10))
    for i,o in enumerate(observations):
        covariance[2*i:2*i+2,2*i:2*i+2] = measurement_covariance(o)
        for j,p in enumerate(observations):
            if (o.station,o.night)==(p.station,p.night):
                covariance[2*i:2*i+2,2*j:2*j+2] += tau*tau*np.eye(2)
    vector = residual.ravel()
    expected = vector@np.linalg.solve(covariance,vector)
    assert np.sum(noise.whiten(residual)**2) == pytest.approx(expected,rel=2e-14)
    permutation = [4,2,0,3,1]
    shuffled = OpticalNoiseModel([observations[i] for i in permutation],tau)
    assert np.sum(shuffled.whiten(residual[permutation])**2) == pytest.approx(expected,rel=2e-14)


def test_same_night_information_saturates_at_systematic_floor():
    training,_,_ = synthetic_case()
    sigma,tau = .2,.15
    for n in (1,4,40):
        observations = [replace(training[0],id=str(i),station='T08',sigma_ra_arcsec=sigma,
                                sigma_dec_arcsec=sigma,correlation=0.) for i in range(n)]
        residual = np.tile([1.,0.],(n,1))
        objective = np.sum(OpticalNoiseModel(observations,tau).whiten(residual)**2)
        assert objective == pytest.approx(1/(sigma*sigma/n+tau*tau),rel=1e-13)
        assert objective < 1/(tau*tau)


def test_zero_night_sigma_matches_legacy_per_exposure_whitening():
    training,_,_ = synthetic_case()
    ra = np.deg2rad([o.ra_deg+.00001 for o in training])
    dec = np.deg2rad([o.dec_deg for o in training])
    vectors = np.c_[np.cos(dec)*np.cos(ra),np.cos(dec)*np.sin(ra),np.sin(dec)]
    raw = angular_residuals(vectors,training)
    assert np.array_equal(OpticalNoiseModel(training,0).whiten(raw),angular_residuals(vectors,training,True))


@pytest.mark.parametrize('sigma',[-.1,float('nan'),11,True,'0.2'])
def test_invalid_systematic_sigma_rejected(sigma):
    training,_,_ = synthetic_case()
    with pytest.raises(ValueError):
        OpticalNoiseModel(training,sigma)


def test_missing_station_does_not_silently_combine_unrelated_observers():
    training,_,_ = synthetic_case()
    with pytest.raises(ValueError,match='station'):
        OpticalNoiseModel(training,.15)


def test_repeated_perfect_images_do_not_erase_orbit_uncertainty():
    training,_,background = synthetic_case()
    repeated = [replace(o,id=f'{o.id}-{j}',station='T08') for o in training for j in range(8)]
    independent = fit_orbit(repeated,background,seeds=[analytic_state(0)])
    correlated = fit_orbit(repeated,background,seeds=[analytic_state(0)],night_systematic_arcsec=.15)
    a = np.trace(np.array(independent['covariance_au_day'])[:3,:3])
    b = np.trace(np.array(correlated['covariance_au_day'])[:3,:3])
    assert b > 3*a
    assert correlated['error_model']['station_night_groups']==14
    assert correlated['training_rms_arcsec'] < 1e-6


def test_pointwise_intervals_use_two_dimensional_probability_and_future_image_noise():
    _,holdout,background = synthetic_case()
    origin = replace(holdout[0],station='T08')
    rng = np.random.default_rng(49018)
    noise = rng.multivariate_normal([0,0],measurement_covariance(origin),size=1000)
    observations = [replace(origin,id=f'image{i}',
        ra_deg=(origin.ra_deg+east/(3600*np.cos(np.deg2rad(origin.dec_deg))))%360,
        dec_deg=origin.dec_deg+north/3600) for i,(east,north) in enumerate(noise)]
    fit = dict(state_au_day=analytic_state(0).tolist(),covariance_au_day=np.zeros((6,6)).tolist(),
               error_model=dict(night_systematic_arcsec=0.))
    uncertainty = {'jacobian_arcsec_per_au_day':np.zeros((1000,2,6)).tolist()}
    result = prediction_coverage(fit,observations,background,uncertainty=uncertainty)
    assert .62 < result['pointwise_68_fraction'] < .74
    assert .92 < result['pointwise_95_fraction'] < .98
    assert result['chi_square_2d_thresholds'][0] == pytest.approx(2.2957489289,rel=1e-9)
    assert result['chi_square_2d_thresholds'][1] == pytest.approx(5.9914645471,rel=1e-9)
    assert result['station_night_count']==1


def test_seasons_are_chosen_using_dates_and_format_only():
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from fetch_orbit_cohort import choose_seasons
    policy = json.loads((ROOT/'scripts/orbit-cohort-policy.json').read_bytes())
    doc = json.loads((ROOT/'src/solar_simulator/data/orbit-cohort-13270.json').read_bytes())
    records = [dict(permid='13270',stn=r['station'],obstime=r['utc'],obsid=r['id'],
                    Obstype='optical',mode='CCD',astcat='Gaia2',subfrm=None,deprecated=None,
                    rmsra=str(r['sigma_ra_arcsec']),rmsdec=str(r['sigma_dec_arcsec']),
                    ra='THIS DOES NOT AFFECT SELECTION',dec='NOR DOES THIS') for r in doc['observations']]
    train,holdout,selection = choose_seasons(records,'13270',policy)
    assert len(train)==136 and len(holdout)==99 and selection['gap_days']>300
    assert {r['obsid'] for r in train}.isdisjoint(r['obsid'] for r in holdout)


def test_declared_unavailable_case_remains_in_manifest():
    manifest = json.loads((ROOT/'docs/orbit-cohort-manifest.json').read_bytes())
    assert len(manifest['cases'])==3
    failed = next(c for c in manifest['cases'] if c['designation']=='32100')
    assert failed['status']=='unavailable'
    assert 'criteria' in failed['reason']


def test_frozen_cohort_has_whole_season_gap_and_multiple_real_stations():
    for designation in ('13270','13271'):
        doc = json.loads((ROOT/f'src/solar_simulator/data/orbit-cohort-{designation}.json').read_bytes())
        training,holdout,background = decode_dataset(doc)
        assert min(o.time_days for o in holdout)-max(o.time_days for o in training)>270
        assert {o.station for o in training+holdout}=={'T05','T08'}
        assert len(background.names)==11
        assert all(name not in background.names for name in ('13270','13271'))
