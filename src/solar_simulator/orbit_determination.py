"""Restricted optical orbit determination in ICRF/SSB, AU and TDB days.

The fitted target is a massless Newtonian particle. Prescribed background
ephemerides and measured observer positions are external inputs. They are not
the target's future trajectory. This module does not replace the closed N-body
simulation, nor infer physical accuracy in metres from angular residuals.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from math import isfinite
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicHermiteSpline
from scipy.linalg import solve_triangular
from scipy.optimize import least_squares

AU_METRES = 149597870700.
ARCSEC_PER_RADIAN = 180 * 3600 / np.pi
LIGHT_AU_DAY = 299792458. * 86400 / AU_METRES


def _number(value, name):
    if isinstance(value, (bool, str)) or not isinstance(value, (int, float, np.number)) or not isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return float(value)


def _vector(value, name, size=3):
    array = np.array(value, dtype=float)
    if array.shape != (size,) or not np.isfinite(array).all():
        raise ValueError(f'{name} must contain {size} finite coordinates')
    # Validate before numpy coercion silently accepts booleans/strings.
    for item in value:
        _number(item, name)
    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class OpticalObservation:
    id: str
    night: str
    time_days: float
    ra_deg: float
    dec_deg: float
    sigma_ra_arcsec: float
    sigma_dec_arcsec: float
    observer_position_au: tuple
    correlation: float = 0.
    station: str = ''

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id or not isinstance(self.night, str):
            raise ValueError('Observation ID and UTC night are required')
        if not isinstance(self.station,str) or (self.station and (len(self.station)!=3 or not self.station.isalnum())):
            raise ValueError('Station must be an MPC three-character code')
        try:
            parsed = datetime.strptime(self.night, '%Y-%m-%d')
        except ValueError as error:
            raise ValueError('Invalid observing night') from error
        if parsed.strftime('%Y-%m-%d') != self.night:
            raise ValueError('Observing night must use YYYY-MM-DD')
        for key in ('time_days', 'ra_deg', 'dec_deg', 'sigma_ra_arcsec', 'sigma_dec_arcsec', 'correlation'):
            _number(getattr(self, key), key)
        if not 0 <= self.ra_deg < 360 or not -90 <= self.dec_deg <= 90:
            raise ValueError('RA/Dec outside their angular ranges')
        if min(self.sigma_ra_arcsec, self.sigma_dec_arcsec) <= 0 or abs(self.correlation) >= 1:
            raise ValueError('Invalid optical covariance')
        object.__setattr__(self, 'observer_position_au', tuple(_vector(self.observer_position_au, 'Observer')))


class EphemerisBackground:
    """Prescribed gravitating bodies; cubic Hermite interpolation without extrapolation."""
    def __init__(self, times_days, names, gm_au3_day2, positions_au, velocities_au_day):
        times = np.asarray(times_days, dtype=float)
        gm = np.asarray(gm_au3_day2, dtype=float)
        positions = np.asarray(positions_au, dtype=float)
        velocities = np.asarray(velocities_au_day, dtype=float)
        if (times.ndim != 1 or len(times) < 2 or not np.isfinite(times).all()
                or np.any(np.diff(times) <= 0)):
            raise ValueError('Background times must strictly increase')
        if (not names or names[0] != 'Sun' or len(set(names)) != len(names)
                or any(not isinstance(n, str) or not n for n in names)):
            raise ValueError('Unique background names must start with Sun')
        if gm.shape != (len(names),) or not np.isfinite(gm).all() or np.any(gm <= 0):
            raise ValueError('Background GM must be positive')
        if (positions.shape != (len(times), len(names), 3) or velocities.shape != positions.shape
                or not np.isfinite(positions).all() or not np.isfinite(velocities).all()):
            raise ValueError('Malformed background states')
        self.names = tuple(names)
        self.gm = gm.copy()
        self.gm.setflags(write=False)
        self.start, self.end = float(times[0]), float(times[-1])
        self.spline = CubicHermiteSpline(times, positions, velocities, axis=0, extrapolate=False)

    def positions(self, times):
        values = np.asarray(times, dtype=float)
        if not np.isfinite(values).all() or np.any(values < self.start) or np.any(values > self.end):
            raise ValueError('Requested time outside background coverage')
        return self.spline(values)

    def acceleration(self, time, position, sun_only=False):
        sources = self.positions(time)
        delta = sources - position
        distances = np.linalg.norm(delta, axis=1)
        if not np.isfinite(distances).all() or np.any(distances < 1e-8):
            raise ValueError('Collision/singular restricted trajectory')
        count = 1 if sun_only else len(self.gm)
        return np.sum(self.gm[:count, None]*delta[:count]/distances[:count, None]**3, axis=0)


def propagate(state, background, times, sun_only=False, rtol=3e-12, atol=1e-13):
    """Integrate forward/backward from t=0, refusing dense-output extrapolation."""
    state = _vector(state, 'Fitted state', 6)
    times = np.asarray(times, dtype=float)
    if times.ndim != 1 or not len(times) or not np.isfinite(times).all():
        raise ValueError('Finite prediction epochs are required')
    if _number(rtol, 'rtol') < 3e-14 or _number(atol, 'atol') <= 0:
        raise ValueError('Invalid numerical tolerances')
    low, high = min(0., float(times.min())), max(0., float(times.max()))
    background.positions([low, high])
    def rhs(time, value):
        return np.r_[value[3:], background.acceleration(time, value[:3], sun_only)]
    solutions = {}
    for end in (low, high):
        if end != 0:
            sol = solve_ivp(rhs, (0., end), state, method='DOP853', rtol=rtol,
                            atol=atol, max_step=2., dense_output=True)
            if not sol.success:
                raise RuntimeError('Orbit integration failed: '+sol.message)
            solutions[end < 0] = sol.sol
    def evaluate(query):
        query = np.atleast_1d(np.asarray(query, dtype=float))
        if not np.isfinite(query).all() or np.any(query < low) or np.any(query > high):
            raise ValueError('Requested target time outside integrated interval')
        values = np.repeat(state[None, :], len(query), axis=0)
        for before in (True, False):
            mask = query < 0 if before else query > 0
            if np.any(mask):
                values[mask] = solutions[before](query[mask]).T
        return values
    return evaluate


def predict_directions(state, observations, background, sun_only=False, rtol=3e-12, atol=1e-13):
    """Astrometric ICRF direction: emission target, reception observer, iterated light time.

    No stellar aberration/refraction: these are catalog-reduced astrometric angles.
    Up to one day of light time is supported; larger ranges fail explicitly.
    """
    observations = tuple(observations)
    if not observations:
        raise ValueError('No optical observations')
    times = np.array([o.time_days for o in observations])
    observer = np.array([o.observer_position_au for o in observations])
    orbit = propagate(state, background, np.r_[times, min(times)-1.], sun_only, rtol, atol)
    emission = times.copy()
    for _ in range(12):
        delta = orbit(emission)[:, :3] - observer
        ranges = np.linalg.norm(delta, axis=1)
        if not np.isfinite(ranges).all() or np.any(ranges <= 0):
            raise ValueError('Undefined observer/target direction')
        revised = times - ranges/LIGHT_AU_DAY
        if np.any(times-revised >= 1.):
            raise ValueError('Target exceeds supported one-day light time')
        if np.max(abs(revised-emission)) < 1e-12:
            delta = orbit(revised)[:, :3] - observer
            return delta / np.linalg.norm(delta, axis=1)[:, None]
        emission = revised
    raise RuntimeError('Light-time iteration did not converge')


def angular_residuals(predicted, observations, weighted=False):
    """Signed east/north log-map residuals in arcsec; stable RA wrap and pole limit.

    Reported rmsRA is interpreted as RA*cos(Dec), per the ADES standard.
    Correlated errors are whitened using the full 2x2 covariance.
    """
    observations = tuple(observations)
    predicted = np.asarray(predicted, dtype=float)
    if predicted.shape != (len(observations), 3) or not np.isfinite(predicted).all():
        raise ValueError('Malformed predicted directions')
    norms = np.linalg.norm(predicted, axis=1)
    if np.any(abs(norms-1) > 1e-10):
        raise ValueError('Predicted directions must be unit vectors')
    ra = np.deg2rad([o.ra_deg for o in observations])
    dec = np.deg2rad([o.dec_deg for o in observations])
    measured = np.column_stack((np.cos(dec)*np.cos(ra), np.cos(dec)*np.sin(ra), np.sin(dec)))
    east = np.column_stack((-np.sin(ra), np.cos(ra), np.zeros(len(ra))))
    north = np.column_stack((-np.sin(dec)*np.cos(ra), -np.sin(dec)*np.sin(ra), np.cos(dec)))
    dot = np.sum(predicted*measured, axis=1)
    components = np.column_stack((np.sum(predicted*east, axis=1), np.sum(predicted*north, axis=1)))
    size = np.linalg.norm(components, axis=1)
    angle = np.arctan2(size, dot)
    if np.any(angle > np.pi/2):
        raise ValueError('Initial direction is more than 90 degrees from observations')
    scale = np.divide(angle, size, out=np.ones_like(angle), where=size > 1e-15)
    residual = components*scale[:, None]*ARCSEC_PER_RADIAN
    if weighted:
        for index, obs in enumerate(observations):
            east_scaled = residual[index, 0]/obs.sigma_ra_arcsec
            north_scaled = residual[index, 1]/obs.sigma_dec_arcsec
            residual[index] = (east_scaled, (north_scaled-obs.correlation*east_scaled)/np.sqrt(1-obs.correlation**2))
    return residual


def measurement_covariance(observation):
    """ADES east/north covariance, arcsec squared; includes per-image RA/Dec correlation."""
    a,b,r = observation.sigma_ra_arcsec,observation.sigma_dec_arcsec,observation.correlation
    return np.array([[a*a,r*a*b],[r*a*b,b*b]])


def station_night_groups(observations):
    groups = {}
    for i,o in enumerate(observations):
        if not o.station:
            raise ValueError('Correlated station/night errors require explicit station codes')
        groups.setdefault((o.station,o.night),[]).append(i)
    return tuple((key,np.array(indices,dtype=int)) for key,indices in groups.items())


class OpticalNoiseModel:
    """GLS with a shared zero-mean east/north station-night offset, marginalized exactly.

    C_group = blockdiag(C_image) + tau^2 (ones(n,n) tensor I_2).
    Tau is an explicit assumption chosen before fit, not inferred from holdout.
    UTC-date grouping is a proxy for observing nights, not a global catalog bias.
    """
    def __init__(self, observations, night_systematic_arcsec=0.):
        self.observations = tuple(observations)
        self.tau = _number(night_systematic_arcsec,'Night systematic sigma')
        if not 0 <= self.tau <= 10:
            raise ValueError('Night systematic sigma must lie within [0,10] arcsec')
        self.groups = ()
        self.cholesky = ()
        if self.tau:
            self.groups = station_night_groups(self.observations)
            blocks = []
            for _,indices in self.groups:
                covariance = np.kron(np.ones((len(indices),len(indices))),self.tau**2*np.eye(2))
                for i,index in enumerate(indices):
                    covariance[2*i:2*i+2,2*i:2*i+2] += measurement_covariance(self.observations[index])
                blocks.append(np.linalg.cholesky(covariance))
            self.cholesky = tuple(blocks)

    def whiten(self, residuals_arcsec):
        values = np.asarray(residuals_arcsec,dtype=float)
        if values.shape != (len(self.observations),2) or not np.isfinite(values).all():
            raise ValueError('Malformed optical residuals')
        result = np.empty_like(values)
        if not self.tau:
            for i,o in enumerate(self.observations):
                east = values[i,0]/o.sigma_ra_arcsec
                north = values[i,1]/o.sigma_dec_arcsec
                result[i] = (east,(north-o.correlation*east)/np.sqrt(1-o.correlation**2))
        else:
            for (_,indices),lower in zip(self.groups,self.cholesky):
                result[indices] = solve_triangular(lower,values[indices].ravel(),lower=True,check_finite=False).reshape(-1,2)
        return result


def initial_states(training, background, ranges_au=(1., 1.5, 2.5, 3.5)):
    """Training-only range hypotheses; no external target orbit or holdout input."""
    training = tuple(training)
    if len(training) < 4 or len({o.night for o in training}) < 3:
        raise ValueError('Need at least three distinct observing nights')
    times = np.array([o.time_days for o in training])
    if np.ptp(times) < 2:
        raise ValueError('Training arc too short for this initial-orbit procedure')
    ra = np.deg2rad([o.ra_deg for o in training])
    dec = np.deg2rad([o.dec_deg for o in training])
    directions = np.column_stack((np.cos(dec)*np.cos(ra), np.cos(dec)*np.sin(ra), np.sin(dec)))
    # Smooth orbit-scale motion, not the station's instantaneous diurnal velocity.
    direction = np.polynomial.polynomial.polyfit(times, directions, 2)
    site = np.polynomial.polynomial.polyfit(times, np.array([o.observer_position_au for o in training]), 2)
    unit = direction[0]/np.linalg.norm(direction[0])
    rate = (direction[1]-unit*np.dot(unit, direction[1]))/np.linalg.norm(direction[0])
    seeds = []
    for distance in ranges_au:
        if _number(distance, 'Initial range') <= 0 or distance > 20:
            raise ValueError('Initial range must lie within (0, 20] AU')
        seeds.append(np.r_[site[0]+distance*unit, site[1]+distance*rate])
    return tuple(seeds)


def fit_orbit(training, background, seeds=None, sun_only=False, max_evaluations=150,
              rtol=3e-12, atol=1e-13, night_systematic_arcsec=0.):
    """Fit six Cartesian parameters using training data exclusively.

    Returned covariance is local, linear and conditional on the fixed physical
    model; it does not include catalog biases, planet/EOP uncertainty or multiple
    disconnected orbit solutions. It is absent for rank-deficient fits.
    """
    training = tuple(training)
    if len(training) < 4 or len({o.id for o in training}) != len(training):
        raise ValueError('At least four distinct training measurements are required')
    if len({o.night for o in training}) < 3 or np.ptp([o.time_days for o in training]) < 2:
        raise ValueError('Insufficient training nights or arc')
    if type(max_evaluations) is not int or not 1 <= max_evaluations <= 2000:
        raise ValueError('max_evaluations must be an integer from 1 to 2000')
    seeds = initial_states(training, background) if seeds is None else tuple(seeds)
    if not seeds:
        raise ValueError('No initial range hypotheses')
    noise = OpticalNoiseModel(training,night_systematic_arcsec)
    def residual(state):
        raw = angular_residuals(predict_directions(state, training, background, sun_only, rtol, atol),training)
        return noise.whiten(raw).ravel()
    attempts, candidates = [], []
    for seed in seeds:
        seed = _vector(seed, 'Initial state', 6)
        try:
            result = least_squares(residual, seed, jac='3-point', x_scale=np.array([1,1,1,.01,.01,.01]),
                diff_step=1e-5, ftol=1e-10, xtol=1e-11, gtol=1e-7, max_nfev=max_evaluations)
            attempts.append(dict(success=bool(result.success), evaluations=result.nfev,
                training_chi_square=float(np.dot(result.fun, result.fun)), message=result.message))
            if result.success and np.isfinite(result.x).all() and np.isfinite(result.jac).all():
                candidates.append(result)
        except (ValueError, RuntimeError, FloatingPointError, OverflowError) as error:
            attempts.append(dict(success=False, message=str(error)))
    if not candidates:
        raise RuntimeError('No initial hypothesis converged: '+str(attempts))
    result = min(candidates, key=lambda c: np.dot(c.fun, c.fun))
    _, singular, vt = np.linalg.svd(result.jac, full_matrices=False)
    rank = int(np.sum(singular > singular[0]*1e-10))
    chi2 = float(np.dot(result.fun, result.fun))
    dof = 2*len(training)-6
    covariance = None
    if rank == 6:
        # Inflate for excess scatter, never shrink quoted observation uncertainties.
        covariance = ((vt.T/singular**2)@vt)*max(1., chi2/dof)
    residual_arcsec = angular_residuals(predict_directions(result.x, training, background, sun_only, rtol, atol), training)
    sun = background.positions(0)[0]
    sun_velocity = background.spline(0, 1)[0]
    relative_r, relative_v = result.x[:3]-sun, result.x[3:]-sun_velocity
    energy = .5*np.dot(relative_v, relative_v)-background.gm[0]/np.linalg.norm(relative_r)
    return dict(state_au_day=result.x.tolist(), rank=rank,
        identifiable_locally=rank == 6, jacobian_condition=float(singular[0]/singular[-1]) if singular[-1] > 0 else None,
        covariance_au_day=covariance.tolist() if covariance is not None else None,
        training_chi_square=chi2, degrees_of_freedom=dof, reduced_chi_square=chi2/dof,
        training_rms_arcsec=float(np.sqrt(np.mean(np.sum(residual_arcsec**2, axis=1)))),
        heliocentric_specific_energy_au2_day2=float(energy),
        attempts=attempts, model='Sun-only Newtonian restricted' if sun_only else 'Prescribed-background Newtonian restricted',
        numerical_tolerances=dict(rtol=rtol, atol_au_and_au_day=atol),
        error_model=dict(night_systematic_arcsec=noise.tau,
            group_definition='MPC station plus UTC observation date' if noise.tau else 'independent exposures',
            station_night_groups=len(noise.groups) if noise.tau else None),
        uncertainty_scope='Local linear covariance conditional on fixed physical/error model; inflated for excess scatter. Station-night common offsets included only at explicitly specified sigma. Global catalog/planet biases and uniqueness are not guaranteed.')


def decode_dataset(document):
    """Strict core schema and chronological/night separation before fitting."""
    if type(document) is not dict or type(document.get('schema_version')) is not int or document['schema_version'] != 1:
        raise ValueError('Unsupported optical dataset schema')
    for key, expected in (('frame','ICRF'), ('center','SSB'), ('units','AU-D'), ('time_scale','TDB')):
        if document.get(key) != expected:
            raise ValueError(f'Optical dataset requires {key}={expected}')
    _number(document['epoch_jd_tdb'], 'Epoch')
    bg = document['background']
    bodies = bg['bodies']
    background = EphemerisBackground(bg['times_days'], [b['name'] for b in bodies],
        [b['gm_au3_day2'] for b in bodies], np.array([b['positions_au'] for b in bodies]).transpose(1,0,2),
        np.array([b['velocities_au_day'] for b in bodies]).transpose(1,0,2))
    training, holdout = [], []
    ids = set()
    for record in document['observations']:
        obs = OpticalObservation(**{key:record[key] for key in OpticalObservation.__dataclass_fields__ if key in record})
        if 'utc' in record:
            stamp = datetime.fromisoformat(record['utc'].replace('Z','+00:00'))
            if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0 or record['utc'][:10] != obs.night:
                raise ValueError('UTC timestamp must agree with the observing night')
            offset = _number(record['utc_to_tdb_seconds'], 'UTC-to-TDB offset')
            converted = 2440587.5+stamp.timestamp()/86400-document['epoch_jd_tdb']+offset/86400
            if abs(converted-obs.time_days) > 1e-8:
                raise ValueError('Inconsistent UTC/TDB observation time')
        if obs.id in ids:
            raise ValueError('Duplicate optical measurement ID')
        ids.add(obs.id)
        if record['split'] not in ('train', 'holdout'):
            raise ValueError('Unknown observation split')
        (training if record['split'] == 'train' else holdout).append(obs)
    if not training or not holdout or max(o.time_days for o in training) >= min(o.time_days for o in holdout):
        raise ValueError('Holdout observations must strictly follow training')
    if {o.night for o in training} & {o.night for o in holdout}:
        raise ValueError('An observing night cannot appear in both splits')
    # Coverage includes light time and epoch: no silent spline extrapolation.
    background.positions([min(0., min(o.time_days for o in training)-1.),
                          max(0., max(o.time_days for o in holdout))])
    return tuple(training), tuple(holdout), background


def evaluate_predictions(fit, observations, background, sun_only=False, rtol=3e-12, atol=1e-13):
    observations = tuple(observations)
    directions = predict_directions(fit['state_au_day'], observations, background, sun_only, rtol, atol)
    residuals = angular_residuals(directions, observations)
    radial = np.linalg.norm(residuals, axis=1)
    weighted = angular_residuals(directions, observations, weighted=True)
    tau = fit.get('error_model',{}).get('night_systematic_arcsec',0.)
    gls = OpticalNoiseModel(observations,tau).whiten(residuals)
    return dict(count=len(observations), nights=len({o.night for o in observations}),
        rms_arcsec=float(np.sqrt(np.mean(radial**2))), median_arcsec=float(np.median(radial)),
        max_arcsec=float(max(radial)), chi_square=float(np.sum(weighted**2)),
        model_chi_square=float(np.sum(gls**2)),
        residuals=[dict(id=o.id, night=o.night, time_days=o.time_days,
            east_arcsec=float(r[0]), north_arcsec=float(r[1]), radial_arcsec=float(s))
            for o, r, s in zip(observations, residuals, radial)])


def prediction_uncertainty(fit, observations, background, sun_only=False, include_jacobian=False):
    """Propagate the local training covariance to sky angles; never refit holdout.

    Linearization uses central differences of predictions, including light time.
    The resulting ellipse is conditional on the fixed background/model and does
    includes the training noise model through its fitted covariance; not global
    catalog biases. Future measurement/nocturnal noise is added by coverage().
    """
    observations = tuple(observations)
    if not observations:
        raise ValueError('Prediction observations are required')
    covariance = fit.get('covariance_au_day')
    if covariance is None:
        return None
    covariance = np.asarray(covariance, dtype=float)
    if (covariance.shape != (6,6) or not np.isfinite(covariance).all()
            or not np.allclose(covariance,covariance.T,rtol=1e-10,atol=1e-25)
            or np.linalg.eigvalsh(covariance).min() < -1e-20):
        raise ValueError('Invalid fitted covariance')
    state = _vector(fit['state_au_day'], 'Fitted state', 6)
    jacobian = np.empty((len(observations),2,6))
    for k, step in enumerate((1e-5,1e-5,1e-5,1e-7,1e-7,1e-7)):
        delta = np.zeros(6)
        delta[k] = step
        plus = angular_residuals(predict_directions(state+delta,observations,background,sun_only),observations)
        minus = angular_residuals(predict_directions(state-delta,observations,background,sun_only),observations)
        jacobian[:,:,k] = (plus-minus)/(2*step)
    sky = np.einsum('nik,kl,njl->nij',jacobian,covariance,jacobian)
    axes = np.sqrt(np.maximum(0,np.linalg.eigvalsh(sky)))
    result = dict(scope='Local linear conditional 1-sigma axes of prediction alone; excluding future measurement noise, global catalog biases and background/model errors.',
        epoch_position_sigma_trace_metres=float(np.sqrt(np.trace(covariance[:3,:3]))*AU_METRES),
        predictions=[dict(id=o.id,time_days=o.time_days,
            covariance_arcsec2=c.tolist(),minor_sigma_arcsec=float(a[0]),major_sigma_arcsec=float(a[1]))
            for o,c,a in zip(observations,sky,axes)])
    if include_jacobian:
        result['jacobian_arcsec_per_au_day'] = jacobian.tolist()
    return result


def prediction_coverage(fit, observations, background, sun_only=False, uncertainty=None):
    """Holdout residuals against prediction + fresh measurement covariance.

    Report pointwise and station-night mean coverage separately. Intervals use
    the 2D chi-square thresholds (68.27%, 95%), not 1D +/-sigma conventions.
    Nights remain mutually correlated through the common fitted orbit; coverage
    fractions are descriptive, not binomial significance or calibration proofs.
    """
    from scipy.stats import chi2
    observations = tuple(observations)
    if uncertainty is None:
        uncertainty = prediction_uncertainty(fit,observations,background,sun_only,include_jacobian=True)
    if uncertainty is None:
        return None
    jacobian = np.asarray(uncertainty['jacobian_arcsec_per_au_day'])
    if jacobian.shape != (len(observations),2,6):
        raise ValueError('Malformed prediction Jacobian')
    residuals = angular_residuals(predict_directions(fit['state_au_day'],observations,background,sun_only),observations)
    state_covariance = np.array(fit['covariance_au_day'])
    tau = fit.get('error_model',{}).get('night_systematic_arcsec',0.)
    thresholds = chi2.ppf([.682689492137,.95],df=2)
    def record(residual,covariance):
        distance = float(residual@np.linalg.solve(covariance,residual))
        return dict(mahalanobis_squared=distance,inside_68_percent=bool(distance<=thresholds[0]),
                    inside_95_percent=bool(distance<=thresholds[1]))
    pointwise = []
    for i,o in enumerate(observations):
        cov = jacobian[i]@state_covariance@jacobian[i].T+measurement_covariance(o)+tau**2*np.eye(2)
        pointwise.append(dict(id=o.id,station=o.station,night=o.night,**record(residuals[i],cov)))
    groups = station_night_groups(observations) if all(o.station for o in observations) else ()
    nightly = []
    for (station,night),indices in groups:
        mean_jacobian = np.mean(jacobian[indices],axis=0)
        cov = mean_jacobian@state_covariance@mean_jacobian.T
        cov += sum((measurement_covariance(observations[i]) for i in indices),np.zeros((2,2)))/len(indices)**2
        cov += tau**2*np.eye(2)
        nightly.append(dict(station=station,night=night,count=len(indices),
                            **record(np.mean(residuals[indices],axis=0),cov)))
    def fraction(records,key):
        return sum(r[key] for r in records)/len(records) if records else None
    return dict(scope='Descriptive conditional coverage; model/background/global catalog errors omitted. Pointwise exposures are not independent; nights share fitted orbit uncertainty.',
        chi_square_2d_thresholds=thresholds.tolist(),pointwise_count=len(pointwise),station_night_count=len(nightly),
        pointwise_68_fraction=fraction(pointwise,'inside_68_percent'),pointwise_95_fraction=fraction(pointwise,'inside_95_percent'),
        station_night_68_fraction=fraction(nightly,'inside_68_percent'),station_night_95_fraction=fraction(nightly,'inside_95_percent'),
        pointwise=pointwise,station_nights=nightly)


def fit_dataset(path, output=None, max_evaluations=150, night_systematic_arcsec=None):
    """Offline chronological validation; holdout is evaluated only after fit returns."""
    if output is not None and Path(output).resolve() == Path(path).resolve():
        raise ValueError('Report must not overwrite the observation dataset')
    raw = Path(path).read_bytes()
    try:
        document = json.loads(raw)
        training, holdout, background = decode_dataset(document)
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError('Malformed optical dataset') from error
    declared_tau = document.get('error_model',{}).get('night_systematic_arcsec',0.)
    tau = declared_tau if night_systematic_arcsec is None else night_systematic_arcsec
    fitted = fit_orbit(training, background, max_evaluations=max_evaluations,night_systematic_arcsec=tau)
    uncertainty = prediction_uncertainty(fitted,holdout,background,include_jacobian=True)
    result = dict(schema_version=1, dataset_sha256=hashlib.sha256(raw).hexdigest(),
        epoch_jd_tdb=document['epoch_jd_tdb'], frame='ICRF', center='SSB', units='AU-D',
        fit=fitted, training=evaluate_predictions(fitted, training, background),
        holdout=evaluate_predictions(fitted, holdout, background),
        holdout_uncertainty={k:v for k,v in uncertainty.items() if k!='jacobian_arcsec_per_au_day'} if uncertainty else None,
        holdout_coverage=prediction_coverage(fitted,holdout,background,uncertainty=uncertainty),
        separation='Initial hypotheses, optimization, multistart selection and covariance use training only. No clipping; every fixed holdout measurement is evaluated.',
        limitation='Angular prediction experiment for one massless target with externally prescribed JPL observer/perturbers; not independent astronomical measurements or a fit of the whole Solar System.')
    if output is not None:
        Path(output).write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2)+'\n', encoding='utf-8')
    return result
