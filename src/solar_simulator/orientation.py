"""Prescribed orientation, independent of the simulated planetary positions.

DE441 lunar mantle Euler angles and ERFA 2.0.1 Vondrak tables are pinned
in package data. ERFA/SOFA heritage and redistribution terms: data/ERFA-LICENSE.txt.
Earth: precession plus the dominant 18.6-year nutation, without fitted frame bias.
This module supplies orientation, not an equation for spin evolution.
"""
from functools import lru_cache
import hashlib
from importlib.resources import files
import json
from math import isfinite
from types import MappingProxyType

import numpy as np
from numpy.polynomial.chebyshev import chebder, chebval

PROFILE_SHA256 = "e2919814946832a4b6635aa0643ce415ffc47fa34945d9c43b53dc61697695eb"
EPOCH = 2461321.5
DURATION = 365.25*86400
CENTURY = 36525*86400
ARCSEC = np.pi/(180*3600)


@lru_cache(maxsize=1)
def profile():
    data = files("solar_simulator.data").joinpath("orientation-de441-20261008.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != PROFILE_SHA256:
        raise ValueError("Изменён закреплённый профиль ориентации DE441")
    def freeze(value):
        if isinstance(value, dict):
            return MappingProxyType({k:freeze(v) for k,v in value.items()})
        if isinstance(value, list):
            return tuple(map(freeze,value))
        return value
    return freeze(json.loads(data))


def validate_time(time):
    if type(time) not in (int, float) or not isfinite(time) or not 0 <= time <= DURATION:
        raise ValueError("Ориентация DE441 доступна только от 2026-10-08 TDB в течение 365.25 суток")


def _periodic(t, table):
    poly = np.asarray(table["polynomial"])
    per = np.asarray(table["periodic"])
    angle = 2*np.pi*t/per[:, 0]
    values = np.cos(angle) @ per[:, 1:3] + np.sin(angle) @ per[:, 3:5]
    return (values + poly @ np.array([1, t, t*t, t*t*t]))*ARCSEC


def precession_matrix(t):
    """J2000 equator to mean equator/equinox of date; t in Julian centuries.

    Algebra and tables from ERFA eraLtp/eraLtpequ/eraLtpecl. Bilinear norms
    allow complex-step differentiation without conjugating the argument.
    """
    tables = profile()["precession"]
    x, y = _periodic(t, tables["ltpequ"])
    equator = np.array([x, y, np.sqrt(1-x*x-y*y)])
    p, q = _periodic(t, tables["ltpecl"])
    w = np.sqrt(1-p*p-q*q)
    eps = 84381.406*ARCSEC  # ERFA model constant, distinct from ECLIPJ2000.
    ecliptic = np.array([p, -q*np.cos(eps)-w*np.sin(eps), -q*np.sin(eps)+w*np.cos(eps)])
    equinox = np.cross(equator, ecliptic)
    equinox /= np.sqrt(equinox @ equinox)
    return np.array([equinox, np.cross(equator, equinox), equator])


def _earth_pole(t):
    omega = ((125*3600+2*60+40.280)-(1934*3600+8*60+10.539)*t+7.455*t*t+0.008*t**3)*ARCSEC
    dpsi = -17.1996*ARCSEC*np.sin(omega)
    deps = 9.2025*ARCSEC*np.cos(omega)
    eps = (84381.448-46.815*t-0.00059*t*t+0.001813*t**3)*ARCSEC
    pole_date = np.array([np.sin(dpsi)*np.sin(eps+deps),
        np.cos(dpsi)*np.cos(eps)*np.sin(eps+deps)-np.sin(eps)*np.cos(eps+deps),
        np.cos(dpsi)*np.sin(eps)*np.sin(eps+deps)+np.cos(eps)*np.cos(eps+deps)])
    return ecliptic_rotation() @ precession_matrix(t).T @ pole_date


def earth_pole(time):
    """Earth pole and its derivative in Ecliptic J2000, seconds from EPOCH."""
    validate_time(time)
    t = (EPOCH-2451545.0)/36525+time/CENTURY
    pole = _earth_pole(t)
    derivative = np.imag(_earth_pole(t+1e-12j))/(1e-12*CENTURY)
    return pole, derivative


def ecliptic_rotation():
    eps = 84381.448*ARCSEC
    return np.array([[1., 0., 0.], [0., np.cos(eps), np.sin(eps)],
                     [0., -np.sin(eps), np.cos(eps)]])


@lru_cache(maxsize=1)
def _lunar_coefficients():
    records = profile()["lunar_records"]
    coefficients = np.asarray([r["coefficients"] for r in records]).reshape(-1, 3, 10)
    derivative = chebder(coefficients, axis=2)*2/(8*86400)
    return (EPOCH-records[0]["start_jd_tdb"])*86400, coefficients, derivative


def lunar_angles(time):
    """DE441 phi, theta, psi (radians), and rates (radians/second)."""
    validate_time(time)
    offset, coefficients, derivative = _lunar_coefficients()
    elapsed = offset+time
    segment = int(elapsed//(8*86400))
    x = 2*(elapsed-segment*8*86400)/(8*86400)-1
    return chebval(x, coefficients[segment].T), chebval(x, derivative[segment].T)


def _rotation(angle, axis):
    c, s = np.cos(angle), np.sin(angle)
    if axis == "z":
        return (np.array([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]]),
                np.array([[-s, -c, 0.], [c, -s, 0.], [0., 0., 0.]]))
    return (np.array([[1., 0., 0.], [0., c, -s], [0., s, c]]),
            np.array([[0., 0., 0.], [0., -s, -c], [0., c, -s]]))


def lunar_rotation(time):
    """DE441 principal axes to Ecliptic J2000, and matrix derivative /s."""
    angles, rates = lunar_angles(time)
    a, da = _rotation(angles[0], "z")
    b, db = _rotation(angles[1], "x")
    c, dc = _rotation(angles[2], "z")
    frame = ecliptic_rotation()
    return frame @ a @ b @ c, frame @ (rates[0]*da@b@c + rates[1]*a@db@c + rates[2]*a@b@dc)
